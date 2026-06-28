"""Summarize a results run into per-model / per-dataset over-refusal metrics.

Reads `responses.jsonl` from a run directory, computes FRR / safe-compliance /
true-refusal / harmful-compliance per (model, dataset), plus a trigger-word
breakdown (RQ4), and writes `metrics.json` + a human-readable table.

Usage:
    python -m scripts.analyze_results results/latest
    python -m scripts.analyze_results results/20260628-120000-smoke
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401  (sys.path shim; -m scripts.x)
except ImportError:
    import _bootstrap  # noqa: F401  (direct file run)

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from orr.evaluation import summarize
from orr.evaluation.metrics import breakdown_by


def _resolve_run_dir(arg: str) -> Path:
    p = Path(arg)
    if p.name == "latest" and not p.exists():
        # follow LATEST.txt fallback
        ptr = p.parent / "LATEST.txt"
        if ptr.exists():
            p = p.parent / ptr.read_text(encoding="utf-8").strip()
    return p


def load_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "responses.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"no responses.jsonl in {run_dir}")
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _fmt(x: float | None) -> str:
    return "  n/a" if x is None else f"{x*100:5.1f}%"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--by-trigger", action="store_true", help="also print trigger-word breakdown (RQ4)")
    args = ap.parse_args(argv)

    run_dir = _resolve_run_dir(args.run_dir)
    rows = load_rows(run_dir)
    if not rows:
        print("[error] no rows", file=sys.stderr)
        return 1

    # group by (model, dataset)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["model"], r["dataset"])].append(r)

    out_metrics: dict = {"run_dir": str(run_dir), "groups": []}

    print(f"\n=== Over-refusal metrics: {run_dir.name} ===\n")
    header = f"{'model':<34} {'dataset':<14} {'n_b':>4} {'n_h':>4} {'FRR':>6} {'SafeC':>6} {'TRR':>6} {'HarmC':>6}"
    print(header)
    print("-" * len(header))

    for (model, dataset), grp in sorted(groups.items()):
        records = [{"gold": r["gold"], "pred": r["pred"]} for r in grp]
        s = summarize(records)
        print(
            f"{model:<34} {dataset:<14} {s.n_benign:>4} {s.n_harmful:>4} "
            f"{_fmt(s.false_refusal_rate)} {_fmt(s.safe_compliance_rate)} "
            f"{_fmt(s.true_refusal_rate)} {_fmt(s.harmful_compliance_rate)}"
        )
        entry = {"model": model, "dataset": dataset, **s.as_dict()}

        if args.by_trigger:
            # explode by individual trigger words on benign prompts
            exploded = []
            for r in grp:
                for tw in (r.get("trigger_words") or ["<none>"]):
                    exploded.append({"gold": r["gold"], "pred": r["pred"], "trigger_word": tw})
            tw_summ = breakdown_by(exploded, "trigger_word")
            entry["by_trigger_word"] = {
                tw: {"frr": ms.false_refusal_rate, "n": ms.n_benign}
                for tw, ms in sorted(tw_summ.items())
            }
        out_metrics["groups"].append(entry)

    (run_dir / "metrics.json").write_text(json.dumps(out_metrics, indent=2), encoding="utf-8")
    print(f"\n[written] {run_dir / 'metrics.json'}")

    if args.by_trigger:
        print("\n--- FRR by trigger word (benign only) ---")
        for entry in out_metrics["groups"]:
            if "by_trigger_word" not in entry:
                continue
            print(f"\n{entry['model']} / {entry['dataset']}:")
            for tw, d in sorted(entry["by_trigger_word"].items(), key=lambda kv: (kv[1]["frr"] is None, -(kv[1]["frr"] or 0))):
                if d["n"]:
                    print(f"  {tw:<22} FRR={_fmt(d['frr'])}  (n={d['n']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
