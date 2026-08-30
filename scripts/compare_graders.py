"""Compare two independent utility graders to check for self-preference bias.

The primary utility scores were produced by qwen2.5-7B, which is also a model
under test — a possible self-preference confound. This runs a second, independent
grader (default gemma2-9B) and reports agreement with the primary grader per
model. High agreement means the quality numbers are not an artifact of one judge.

Usage:
    # 1. produce the second grading (slow — LLM calls)
    python -m scripts.score_utility \
        --grader-model gemma2:9b-instruct-q4_K_M --out results/utility_scores_gemma.json
    # 2. compare
    python -m scripts.compare_graders \
        results/utility_scores.json results/utility_scores_gemma.json
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import json
from pathlib import Path


def _pearson(xs, ys) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("primary")
    ap.add_argument("second")
    ap.add_argument("--metric", default="quality_given_complied",
                    choices=["quality_given_complied", "effective_utility"])
    args = ap.parse_args(argv)

    a = json.loads(Path(args.primary).read_text(encoding="utf-8"))
    b = json.loads(Path(args.second).read_text(encoding="utf-8"))
    models = [m for m in a if m in b]
    if not models:
        print("[error] no shared models between the two grader files")
        return 1

    print(f"\n=== Grader agreement on '{args.metric}' ===\n")
    print(f"{'model':<34} {'primary':>8} {'second':>8} {'|diff|':>7}")
    print("-" * 60)
    xs, ys = [], []
    for m in sorted(models):
        pa, pb = a[m][args.metric], b[m][args.metric]
        xs.append(pa)
        ys.append(pb)
        print(f"{m:<34} {pa:>8.2f} {pb:>8.2f} {abs(pa-pb):>7.2f}")

    mad = sum(abs(x - y) for x, y in zip(xs, ys)) / len(xs)
    print(f"\nmean absolute difference : {mad:.3f}")
    print(f"Pearson correlation      : {_pearson(xs, ys):.3f}")
    print("\nHigh correlation + small MAD => the quality scores are robust to the "
          "choice of grader, so the self-preference concern is not driving them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
