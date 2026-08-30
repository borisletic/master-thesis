"""Confidence intervals and significance tests for the headline results.

The point estimates in the sweep are proportions over small samples (18 hard-tier
benign prompts, 24 harmful controls), so this reports what the data actually
supports: Wilson 95% intervals for every cell, and Holm-corrected Fisher exact
tests for the pairwise model comparisons the thesis makes.

Usage:
    python -m scripts.analyze_stats
    python -m scripts.analyze_stats --out results/stats.json
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from orr.datasets import load_security_swe
from orr.evaluation.stats import fisher_exact, holm_bonferroni, wilson_ci

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"

SHORT = {
    "mistral:latest": "mistral-7B",
    "phi3.5:3.8b-mini-instruct-q4_0": "phi-3.5",
    "qwen2.5:7b-instruct-q4_K_M": "qwen Q4",
    "qwen2.5:7b-instruct-q8_0": "qwen Q8",
    "gemma2:9b-instruct-q4_K_M": "gemma2-9B",
    "llama3.1:8b-instruct-q4_K_M": "llama3.1-8B",
}


def load(globs=("2026*sweep*", "*hard2*"), name="responses_hybrid.jsonl") -> list[dict]:
    """Load responses across one or more dir globs.

    The hard tier is split across two runs: sweep dirs hold sec-bh-001..018, the
    hard2 dirs hold the 82-prompt expansion (sec-bh-019..100). Reading both gives
    the full 100-prompt hard tier, so FRR-hard confidence intervals reflect n=100.
    Deduplicates on (model, prompt_id): if a prompt appears in more than one dir,
    the last one wins.
    """
    if isinstance(globs, str):
        globs = (globs,)
    tier = {p.id: p.tier for p in load_security_swe()}
    seen: dict[tuple[str, str], dict] = {}
    dirs = []
    for g in globs:
        dirs.extend(sorted(_RESULTS.glob(g)))
    for d in dirs:
        f = d / name
        if not f.exists():
            continue
        for line in f.open(encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                r["tier"] = tier.get(r["prompt_id"], "core")
                seen[(r["model"], r["prompt_id"])] = r
    return list(seen.values())


def counts(rows, model, dataset, gold, tier=None) -> tuple[int, int]:
    sel = [r for r in rows
           if r["model"] == model and r["dataset"] == dataset and r["gold"] == gold
           and (tier is None or r["tier"] == tier)]
    return sum(1 for r in sel if r["pred"] == "refusal"), len(sel)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glob", nargs="+", default=["2026*sweep*", "*hard2*"],
                    help="one or more dir globs; hard tier spans sweep + hard2")
    ap.add_argument("--responses-name", default="responses_hybrid.jsonl")
    ap.add_argument("--out", default=str(_RESULTS / "stats.json"))
    args = ap.parse_args(argv)

    rows = load(args.glob, args.responses_name)
    if not rows:
        print("[error] no rows found")
        return 1
    models = [m for m in SHORT if any(r["model"] == m for r in rows)]

    report: dict = {"intervals": {}, "comparisons": {}}

    # ---------------------------------------------------------------- intervals
    print("\n=== 95% Wilson intervals (security_swe) ===\n")
    hdr = f"{'model':<14} {'FRR hard':>22} {'TRR (harmful)':>22}"
    print(hdr); print("-" * len(hdr))
    hard, harmful = {}, {}
    for m in models:
        kh, nh = counts(rows, m, "security_swe", "should_comply", tier="hard")
        kt, nt = counts(rows, m, "security_swe", "should_refuse")
        hard[m], harmful[m] = (kh, nh), (kt, nt)
        ci_h, ci_t = wilson_ci(kh, nh), wilson_ci(kt, nt)
        print(f"{SHORT[m]:<14} {ci_h.fmt():>22} {ci_t.fmt():>22}")
        report["intervals"][SHORT[m]] = {"frr_hard": ci_h.as_dict(),
                                         "trr": ci_t.as_dict()}

    widths = [wilson_ci(*hard[m]).width_pp for m in models]
    print(f"\nCI width on the hard tier: {min(widths):.0f}–{max(widths):.0f} pp "
          f"(n = {hard[models[0]][1]} prompts, so one prompt "
          f"= {100/hard[models[0]][1]:.1f} pp)")

    # -------------------------------------------------------------- comparisons
    for label, data in (("FRR hard", hard), ("TRR harmful", harmful)):
        raw = {}
        for m1, m2 in combinations(models, 2):
            k1, n1 = data[m1]
            k2, n2 = data[m2]
            raw[f"{SHORT[m1]} vs {SHORT[m2]}"] = fisher_exact(k1, n1 - k1, k2, n2 - k2)
        adj = holm_bonferroni(raw)
        report["comparisons"][label] = adj

        print(f"\n=== Pairwise {label} — Fisher exact, Holm-corrected ===\n")
        print(f"{'comparison':<30} {'p_raw':>8} {'p_adj':>8}  verdict")
        print("-" * 62)
        for name, v in sorted(adj.items(), key=lambda kv: kv[1]["p_raw"]):
            mark = "significant" if v["significant"] else "n.s."
            print(f"{name:<30} {v['p_raw']:>8.4f} {v['p_adj']:>8.4f}  {mark}")
        n_sig = sum(1 for v in adj.values() if v["significant"])
        print(f"\n-> {n_sig} of {len(adj)} comparisons survive correction.")

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[written] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
