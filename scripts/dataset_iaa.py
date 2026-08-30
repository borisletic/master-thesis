"""Inter-annotator agreement on the dataset's own gold labels.

Distinct from scripts/make_validation_sample.py, which validates the *classifier*.
This validates the *dataset*: does a second annotator agree that a prompt is
should-comply vs should-refuse? This is the κ the thesis limitations flagged as
missing, and it matters most on the `contested` hard prompts.

Workflow:
  1. export a stratified sample (oversampling contested + harmful):
       python -m scripts.dataset_iaa --export --n 60
     -> results/dataset_iaa_sample.csv with a blank `annotator2_label` column
  2. a second annotator fills `annotator2_label` (should_comply / should_refuse)
  3. score:
       python -m scripts.dataset_iaa --score
     -> agreement + Cohen's κ overall, and separately on contested prompts
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import csv
import random
from pathlib import Path

from orr.datasets import load_security_swe
from orr.evaluation.stats import fisher_exact  # noqa: F401  (kept for parity)

_REPO = Path(__file__).resolve().parents[1]
_OUT = _REPO / "results" / "dataset_iaa_sample.csv"


def _kappa(a: list[str], b: list[str]) -> float:
    labels = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def export(n: int, seed: int) -> Path:
    prompts = load_security_swe()
    rng = random.Random(seed)
    contested = [p for p in prompts if p.meta.get("contested")]
    harmful = [p for p in prompts if p.gold == "should_refuse"]
    other = [p for p in prompts if not p.meta.get("contested") and p.gold == "should_comply"]
    for pool in (contested, harmful, other):
        rng.shuffle(pool)

    # oversample the genuinely debatable cases + a harmful anchor + benign spread
    n_con = min(len(contested), round(n * 0.45))
    n_harm = min(len(harmful), round(n * 0.25))
    n_oth = max(0, n - n_con - n_harm)
    sample = contested[:n_con] + harmful[:n_harm] + other[:n_oth]
    rng.shuffle(sample)

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    with _OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "category", "tier", "contested", "gold_label",
                    "annotator2_label", "prompt"])
        for p in sample:
            w.writerow([p.id, p.category, p.tier, bool(p.meta.get("contested")),
                        p.gold, "", p.text[:300]])
    print(f"[written] {_OUT}  ({len(sample)} rows: {n_con} contested, "
          f"{n_harm} harmful, {n_oth} other)")
    print("Second annotator fills 'annotator2_label' with: should_comply / should_refuse")
    print("Then: python -m scripts.dataset_iaa --score")
    return _OUT


def score() -> int:
    if not _OUT.exists():
        print(f"[error] {_OUT} not found; run --export first.")
        return 1
    rows = [r for r in csv.DictReader(_OUT.open(encoding="utf-8"))
            if (r.get("annotator2_label") or "").strip()]
    if not rows:
        print("[error] no rows with annotator2_label filled in.")
        return 1
    g = [r["gold_label"].strip() for r in rows]
    a2 = [r["annotator2_label"].strip() for r in rows]
    acc = sum(1 for x, y in zip(g, a2) if x == y) / len(rows)
    print(f"n labeled          : {len(rows)}")
    print(f"agreement          : {acc*100:.1f}%")
    print(f"Cohen's kappa      : {_kappa(g, a2):.3f}")

    con = [i for i, r in enumerate(rows) if r["contested"].strip().lower() == "true"]
    if con:
        gc = [g[i] for i in con]
        ac = [a2[i] for i in con]
        acc_c = sum(1 for x, y in zip(gc, ac) if x == y) / len(con)
        print(f"\ncontested prompts  : n={len(con)}  agreement={acc_c*100:.1f}%  "
              f"kappa={_kappa(gc, ac):.3f}")
        print("  (lower agreement here is expected and is the point — it quantifies "
              "how debatable the boundary cases are.)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    if args.export:
        export(args.n, args.seed)
        return 0
    if args.score:
        return score()
    ap.error("specify --export or --score")


if __name__ == "__main__":
    raise SystemExit(main())
