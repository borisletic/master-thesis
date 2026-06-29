"""Re-score saved responses with a different classifier (no re-inference).

The sweep ran with the fast `heuristic` classifier, which under-counts soft /
redirect refusals (esp. contextual XSTest categories). This re-runs the **hybrid**
classifier (heuristic + LLM-judge on ambiguous cases) over the *already-saved*
responses, writing `responses_hybrid.jsonl` alongside each run's `responses.jsonl`.

Prompt text is reconstructed from `prompt_id` via the dataset loaders (the runner
stores ids, not text). Only heuristic-ambiguous rows hit the judge, so this is much
cheaper than re-generating.

Usage:
    python -m scripts.reclassify --glob '*sweep*' --judge-model qwen2.5:7b-instruct-q4_K_M
    python -m scripts.reclassify --dirs results/foo --out-name responses_hybrid.jsonl
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import json
from pathlib import Path

from orr.classification import RefusalClassifier
from orr.datasets import load_dataset
from orr.inference import OllamaRunner

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"


def build_id2text(datasets: set[str]) -> dict[str, str]:
    id2text: dict[str, str] = {}
    for ds in datasets:
        try:
            for p in load_dataset(ds):
                id2text[str(p.id)] = p.text
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] could not load dataset {ds!r}: {exc}")
    return id2text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glob", default="*sweep*")
    ap.add_argument("--dirs", nargs="*")
    ap.add_argument("--judge-model", default="qwen2.5:7b-instruct-q4_K_M")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--out-name", default="responses_hybrid.jsonl")
    ap.add_argument("--mode", choices=["hybrid", "heuristic"], default="hybrid")
    args = ap.parse_args(argv)

    dirs = [Path(d) for d in args.dirs] if args.dirs else sorted(_RESULTS.glob(args.glob))
    dirs = [d for d in dirs if (d / "responses.jsonl").exists()]
    if not dirs:
        print(f"[error] no run dirs (glob={args.glob!r})")
        return 1

    # which datasets appear across these dirs?
    datasets: set[str] = set()
    for d in dirs:
        with (d / "responses.jsonl").open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    datasets.add(json.loads(line)["dataset"])
    id2text = build_id2text(datasets)
    print(f"[reclassify] {len(dirs)} dirs, datasets={sorted(datasets)}, {len(id2text)} prompt texts")

    runner = OllamaRunner(host=args.host)
    if args.mode == "hybrid" and not runner.is_up():
        print(f"[error] Ollama not reachable at {args.host}; needed for the judge.")
        return 2
    classifier = RefusalClassifier(runner=runner, judge_model=args.judge_model, mode=args.mode)

    grand_judged = 0
    for d in dirs:
        rows = [json.loads(l) for l in (d / "responses.jsonl").open(encoding="utf-8") if l.strip()]
        judged = changed = 0
        out_rows = []
        for r in rows:
            text = id2text.get(str(r["prompt_id"]), "")
            cls = classifier.classify(text, r.get("response", ""))
            if cls.source == "llm_judge":
                judged += 1
            if cls.label.value != r["pred"]:
                changed += 1
            nr = dict(r)
            nr["pred"] = cls.label.value
            nr["pred_source"] = cls.source
            nr["pred_confidence"] = round(cls.confidence, 3)
            out_rows.append(nr)
        out_path = d / args.out_name
        with out_path.open("w", encoding="utf-8") as f:
            for nr in out_rows:
                f.write(json.dumps(nr, ensure_ascii=False) + "\n")
        grand_judged += judged
        print(f"  {d.name}: {len(rows)} rows, {judged} judged, {changed} relabeled -> {args.out_name}")

    print(f"[done] total judge calls: {grand_judged}")
    print("[next] python -m scripts.aggregate_sweep --by-tier --by-xstest-type --responses-name responses_hybrid.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
