"""Validate the refusal classifier against human labels.

Workflow:
  1. Run an experiment to produce results/<run>/responses.jsonl.
  2. `python -m scripts.validate_classifier results/<run> --sample 60 --export`
     -> writes a `validation_sample.csv` with a blank `human_label` column.
  3. A human fills `human_label` (refusal/partial/compliance) in that CSV.
  4. `python -m scripts.validate_classifier results/<run> --score`
     -> reports agreement (accuracy, per-class) between classifier and human,
        plus Cohen's kappa.

This supplies the "classifier validated on a human-labeled sample" evidence the
methodology requires (the refusal/comply distinction is objective, so agreement
should be high).
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401  (sys.path shim; -m scripts.x)
except ImportError:
    import _bootstrap  # noqa: F401  (direct file run)

import argparse
import csv
import json
import random
from pathlib import Path


def load_rows(run_dir: Path) -> list[dict]:
    with (run_dir / "responses.jsonl").open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def export_sample(run_dir: Path, n: int, seed: int) -> Path:
    rows = load_rows(run_dir)
    random.Random(seed).shuffle(rows)
    sample = rows[:n]
    out = run_dir / "validation_sample.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["prompt_id", "model", "gold", "classifier_pred", "human_label", "response"])
        for r in sample:
            w.writerow([
                r["prompt_id"], r["model"], r["gold"], r["pred"], "",
                (r.get("response") or "").replace("\n", " ")[:500],
            ])
    return out


def cohens_kappa(a: list[str], b: list[str]) -> float:
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = 0.0
    for lab in labels:
        pa = a.count(lab) / n
        pb = b.count(lab) / n
        pe += pa * pb
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def score(run_dir: Path) -> int:
    path = run_dir / "validation_sample.csv"
    if not path.exists():
        print(f"[error] {path} not found — run with --export first and fill human_label.")
        return 1
    pairs: list[tuple[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            human = (row.get("human_label") or "").strip().lower()
            if human:
                pairs.append((row["classifier_pred"].strip().lower(), human))
    if not pairs:
        print("[error] no rows with human_label filled in.")
        return 1
    clf, hum = [p[0] for p in pairs], [p[1] for p in pairs]
    acc = sum(1 for c, h in zip(clf, hum) if c == h) / len(pairs)
    kappa = cohens_kappa(clf, hum)
    print(f"n labeled          : {len(pairs)}")
    print(f"agreement (acc)    : {acc*100:.1f}%")
    print(f"Cohen's kappa      : {kappa:.3f}")
    # per-class recall vs human
    for lab in sorted(set(hum)):
        idx = [i for i, h in enumerate(hum) if h == lab]
        if idx:
            correct = sum(1 for i in idx if clf[i] == lab)
            print(f"  {lab:<12} human n={len(idx):>3}  classifier-correct={correct/len(idx)*100:.0f}%")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--export", action="store_true", help="export a sample CSV for human labeling")
    ap.add_argument("--score", action="store_true", help="score classifier vs filled human_label")
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)
    run_dir = Path(args.run_dir)

    if args.export:
        out = export_sample(run_dir, args.sample, args.seed)
        print(f"[written] {out}\nFill the 'human_label' column, then run --score.")
        return 0
    if args.score:
        return score(run_dir)
    ap.error("specify --export or --score")


if __name__ == "__main__":
    raise SystemExit(main())
