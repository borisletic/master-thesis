"""Aggregate the RQ3 temperature-repeat runs into mean+/-std per (model, temperature).

Reads the `rq3-*` run dirs (default: the validated `responses_hybrid.jsonl`),
parses model/temp/rep from the tag, computes FRR and TRR per repeat, then reports
mean +/- std across repeats — so the qwen Q4 vs Q8 quantization comparison comes with
a sense of whether the difference exceeds sampling noise.

Usage:
    python -m scripts.aggregate_rq3                      # hybrid labels
    python -m scripts.aggregate_rq3 --responses-name responses.jsonl   # heuristic
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from orr.evaluation import summarize
from orr.evaluation.metrics import mean_std

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"

_TAG = re.compile(r"rq3-(?P<model>.+?)-t(?P<temp>[0-9.]+)-r(?P<rep>\d+)$")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--responses-name", default="responses_hybrid.jsonl")
    ap.add_argument("--glob", default="*rq3*")
    args = ap.parse_args(argv)

    # per (model, temp) -> list of (frr, trr) across reps
    cells: dict[tuple[str, float], list[tuple[float | None, float | None]]] = defaultdict(list)
    for d in sorted(_RESULTS.glob(args.glob)):
        m = _TAG.search(d.name)
        f = d / args.responses_name
        if not m or not f.exists():
            continue
        rows = [json.loads(l) for l in f.open(encoding="utf-8") if l.strip()]
        s = summarize([{"gold": r["gold"], "pred": r["pred"]} for r in rows])
        cells[(m["model"], float(m["temp"]))].append((s.false_refusal_rate, s.true_refusal_rate))

    if not cells:
        print(f"[error] no rq3 dirs with {args.responses_name}")
        return 1

    print(f"\n=== RQ3 quantization x temperature (security_swe, {args.responses_name}) ===")
    print(f"{'model':<28} {'temp':>5} {'reps':>4}   {'FRR mean+/-std':>16}   {'TRR mean+/-std':>16}")
    print("-" * 78)
    for (model, temp) in sorted(cells):
        vals = cells[(model, temp)]
        fr_m, fr_s = mean_std([v[0] for v in vals])
        tr_m, tr_s = mean_std([v[1] for v in vals])
        n = len(vals)
        print(f"{model:<28} {temp:>5} {n:>4}   {fr_m*100:6.1f} +/- {fr_s*100:4.1f}%   {tr_m*100:6.1f} +/- {tr_s*100:4.1f}%")

    # quant deltas at each temp
    models = sorted({m for (m, _t) in cells})
    if len(models) == 2:
        q4 = [m for m in models if "q4" in m.lower()][:1]
        q8 = [m for m in models if "q8" in m.lower()][:1]
        if q4 and q8:
            print("\n--- Q8 minus Q4 (positive = Q8 higher) ---")
            temps = sorted({t for (_m, t) in cells})
            for t in temps:
                if (q4[0], t) in cells and (q8[0], t) in cells:
                    f4, _ = mean_std([v[0] for v in cells[(q4[0], t)]])
                    f8, _ = mean_std([v[0] for v in cells[(q8[0], t)]])
                    t4, _ = mean_std([v[1] for v in cells[(q4[0], t)]])
                    t8, _ = mean_std([v[1] for v in cells[(q8[0], t)]])
                    print(f"  temp {t}: dFRR = {(f8-f4)*100:+.1f}pp   dTRR = {(t8-t4)*100:+.1f}pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
