"""Build a human-validation sample that adjudicates heuristic vs. hybrid classifier.

The heuristic and the LLM-judge (hybrid) disagree on a large fraction of responses,
which swings absolute FRR/TRR 2-4x. Only human labels can decide which classifier
to trust. This pools all sweep responses, joins the heuristic pred with the hybrid
pred, and exports a stratified sample that **oversamples disagreement cases** (the
informative decision-boundary) while keeping coverage across datasets and gold
classes. A human fills `human_label`; `--score` then reports agreement + Cohen's κ
of the human against BOTH classifiers, so we can pick the better one.

Usage:
    python -m scripts.make_validation_sample --export --n 90
    # ...fill human_label (refusal/partial/compliance) in the CSV...
    python -m scripts.make_validation_sample --score
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from orr.datasets import load_dataset

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"
_OUT = _RESULTS / "validation_sample.csv"


def _id2text() -> dict[str, str]:
    m: dict[str, str] = {}
    for ds in ("security_swe", "xstest"):
        try:
            for p in load_dataset(ds):
                m[str(p.id)] = p.text
        except Exception:  # noqa: BLE001
            pass
    return m


def _pool(glob: str) -> list[dict]:
    """Join heuristic + hybrid preds per (model, prompt_id) across all sweep dirs."""
    id2text = _id2text()
    rows: list[dict] = []
    for d in sorted(_RESULTS.glob(glob)):
        heur = d / "responses.jsonl"
        hyb = d / "responses_hybrid.jsonl"
        if not (heur.exists() and hyb.exists()):
            continue
        hmap = {(r["model"], r["prompt_id"]): r
                for r in (json.loads(l) for l in hyb.open(encoding="utf-8") if l.strip())}
        for line in heur.open(encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r["model"], r["prompt_id"])
            hr = hmap.get(key)
            if hr is None:
                continue
            rows.append({
                "prompt_id": r["prompt_id"],
                "model": r["model"],
                "dataset": r["dataset"],
                "gold": r["gold"],
                "heuristic_pred": r["pred"],
                "hybrid_pred": hr["pred"],
                "agree": r["pred"] == hr["pred"],
                "prompt": id2text.get(str(r["prompt_id"]), ""),
                "response": (r.get("response") or "").replace("\n", " ")[:600],
            })
    return rows


def export(n: int, seed: int, glob: str) -> Path:
    rows = _pool(glob)
    disagree = [r for r in rows if not r["agree"]]
    agree = [r for r in rows if r["agree"]]
    rng = random.Random(seed)

    # ~60% disagreement (informative), ~40% agreement; stratify by dataset within each
    n_dis = min(len(disagree), round(n * 0.6))
    n_agr = min(len(agree), n - n_dis)

    def strat(pool: list[dict], k: int) -> list[dict]:
        by_ds: dict[str, list[dict]] = defaultdict(list)
        for r in pool:
            by_ds[r["dataset"]].append(r)
        for v in by_ds.values():
            rng.shuffle(v)
        out, i = [], 0
        keys = list(by_ds)
        while len(out) < k and any(by_ds.values()):
            ds = keys[i % len(keys)]
            if by_ds[ds]:
                out.append(by_ds[ds].pop())
            i += 1
        return out

    sample = strat(disagree, n_dis) + strat(agree, n_agr)
    rng.shuffle(sample)

    with _OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["prompt_id", "model", "dataset", "gold", "heuristic_pred",
                    "hybrid_pred", "human_label", "prompt", "response"])
        for r in sample:
            w.writerow([r["prompt_id"], r["model"], r["dataset"], r["gold"],
                        r["heuristic_pred"], r["hybrid_pred"], "",
                        r["prompt"][:300], r["response"]])
    print(f"[written] {_OUT}  ({len(sample)} rows: {n_dis} disagreement, {n_agr} agreement)")
    print("Fill the 'human_label' column with: refusal / partial / compliance")
    print("Then: python -m scripts.make_validation_sample --score")
    return _OUT


def _kappa(a: list[str], b: list[str]) -> float:
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def score() -> int:
    if not _OUT.exists():
        print(f"[error] {_OUT} not found; run --export first.")
        return 1
    rows = [r for r in csv.DictReader(_OUT.open(encoding="utf-8"))
            if (r.get("human_label") or "").strip()]
    if not rows:
        print("[error] no rows with human_label filled in.")
        return 1
    human = [r["human_label"].strip().lower() for r in rows]
    heur = [r["heuristic_pred"].strip().lower() for r in rows]
    hyb = [r["hybrid_pred"].strip().lower() for r in rows]

    def report(name: str, pred: list[str]) -> None:
        acc = sum(1 for p, h in zip(pred, human) if p == h) / len(human)
        print(f"  {name:<10} acc={acc*100:5.1f}%   kappa={_kappa(pred, human):.3f}")

    print(f"n labeled: {len(rows)}\nHuman vs classifier:")
    report("heuristic", heur)
    report("hybrid", hyb)
    # which wins on the disagreement subset specifically
    dis = [i for i in range(len(rows)) if heur[i] != hyb[i]]
    if dis:
        h_ok = sum(1 for i in dis if heur[i] == human[i])
        y_ok = sum(1 for i in dis if hyb[i] == human[i])
        print(f"\nOn {len(dis)} disagreement cases: heuristic correct {h_ok}, hybrid correct {y_ok}"
              f"  -> winner: {'hybrid' if y_ok > h_ok else 'heuristic' if h_ok > y_ok else 'tie'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--n", type=int, default=90)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--glob", default="2026*sweep*")
    args = ap.parse_args(argv)
    if args.export:
        export(args.n, args.seed, args.glob)
        return 0
    if args.score:
        return score()
    ap.error("specify --export or --score")


if __name__ == "__main__":
    raise SystemExit(main())
