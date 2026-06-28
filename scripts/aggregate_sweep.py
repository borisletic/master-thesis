"""Aggregate multiple per-model run dirs into one cross-model comparison.

The sweep writes one run dir per model (`results/*-sweep-<model>`). This script
collects them into a single table: FRR / TRR per (model, dataset), with optional
breakdowns by security-SWE tier (core vs hard) and by XSTest prompt type (RQ4).

Usage:
    python -m scripts.aggregate_sweep                      # all results/*sweep* dirs
    python -m scripts.aggregate_sweep --glob '*sweep*' --by-tier --by-xstest-type
    python -m scripts.aggregate_sweep --dirs results/a results/b
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401  (sys.path shim; -m scripts.x)
except ImportError:
    import _bootstrap  # noqa: F401  (direct file run)

import argparse
import json
from collections import defaultdict
from pathlib import Path

from orr.datasets import load_security_swe
from orr.evaluation import summarize

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"


def _load_dir(d: Path) -> list[dict]:
    f = d / "responses.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.open(encoding="utf-8") if l.strip()]


def _fmt(x: float | None) -> str:
    return "  n/a" if x is None else f"{x*100:5.1f}%"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glob", default="*sweep*", help="dir glob under results/")
    ap.add_argument("--dirs", nargs="*", help="explicit run dirs (overrides --glob)")
    ap.add_argument("--by-tier", action="store_true", help="split security_swe by core/hard tier")
    ap.add_argument("--by-xstest-type", action="store_true", help="XSTest FRR by prompt type")
    ap.add_argument("--out", default=None, help="write combined metrics JSON here")
    args = ap.parse_args(argv)

    dirs = [Path(d) for d in args.dirs] if args.dirs else sorted(_RESULTS.glob(args.glob))
    dirs = [d for d in dirs if (d / "responses.jsonl").exists()]
    if not dirs:
        print(f"[error] no run dirs with responses.jsonl (glob={args.glob!r})")
        return 1

    tier = {p.id: p.tier for p in load_security_swe()}

    # gather all rows, tag tier
    all_rows: list[dict] = []
    for d in dirs:
        for r in _load_dir(d):
            r["tier"] = tier.get(r["prompt_id"], "core")
            all_rows.append(r)

    # group by (model, dataset)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in all_rows:
        groups[(r["model"], r["dataset"])].append(r)

    print(f"\n=== Cross-model over-refusal sweep ({len(dirs)} run dirs) ===\n")
    header = f"{'model':<34} {'dataset':<14} {'n_b':>4} {'n_h':>4} {'FRR':>6} {'TRR':>6} {'HarmC':>6}"
    print(header)
    print("-" * len(header))
    combined: dict = {"models": []}
    for (model, dataset), grp in sorted(groups.items()):
        s = summarize([{"gold": r["gold"], "pred": r["pred"]} for r in grp])
        print(f"{model:<34} {dataset:<14} {s.n_benign:>4} {s.n_harmful:>4} "
              f"{_fmt(s.false_refusal_rate)} {_fmt(s.true_refusal_rate)} "
              f"{_fmt(s.harmful_compliance_rate)}")
        combined["models"].append({"model": model, "dataset": dataset, **s.as_dict()})

    if args.by_tier:
        print("\n--- security_swe FRR by tier (benign only) ---")
        print(f"{'model':<34} {'core':>10} {'hard':>10}")
        for model in sorted({m for (m, ds) in groups if ds == "security_swe"}):
            rows = [r for r in groups[(model, "security_swe")] if r["gold"] == "should_comply"]
            core = summarize([{"gold": r["gold"], "pred": r["pred"]} for r in rows if r["tier"] == "core"])
            hard = summarize([{"gold": r["gold"], "pred": r["pred"]} for r in rows if r["tier"] == "hard"])
            print(f"{model:<34} {_fmt(core.false_refusal_rate):>10} {_fmt(hard.false_refusal_rate):>10}")

    if args.by_xstest_type:
        print("\n--- XSTest FRR by prompt type (safe prompts; RQ4 lexical-vs-contextual) ---")
        for model in sorted({m for (m, ds) in groups if ds == "xstest"}):
            rows = [r for r in groups[(model, "xstest")] if r["gold"] == "should_comply"]
            by: dict[str, list[dict]] = defaultdict(list)
            for r in rows:
                by[r["category"]].append(r)
            print(f"\n{model}:")
            ranked = sorted(by.items(), key=lambda kv: -(summarize(
                [{"gold": x["gold"], "pred": x["pred"]} for x in kv[1]]).false_refusal_rate or 0))
            for cat, rs in ranked:
                s = summarize([{"gold": x["gold"], "pred": x["pred"]} for x in rs])
                print(f"  {cat:<28} {_fmt(s.false_refusal_rate)}  (n={s.n_benign})")

    if args.out:
        Path(args.out).write_text(json.dumps(combined, indent=2), encoding="utf-8")
        print(f"\n[written] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
