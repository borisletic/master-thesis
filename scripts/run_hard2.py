"""Run the six sweep models on the NEW hard-tier prompts (sec-bh-019..100).

Expanding the hard tier from 18 to 100 prompts only narrows the confidence
intervals if the models are actually evaluated on the new prompts. The original
66 (core + first 18 hard) already have responses in results/*sweep*; this runs
only the 82 new prompts, into results/*-hard2-<model>, so the aggregator can then
combine both and report FRR over the full 100-prompt hard tier.

Resumable: a model whose dir already has all new prompts is skipped.

Usage:
    python -m scripts.run_hard2
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import datetime as dt
import json
from pathlib import Path

from orr.classification import RefusalClassifier
from orr.datasets import load_security_swe
from orr.inference import OllamaRunner

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"

MODELS = [
    "mistral:latest",
    "phi3.5:3.8b-mini-instruct-q4_0",
    "qwen2.5:7b-instruct-q4_K_M",
    "qwen2.5:7b-instruct-q8_0",
    "gemma2:9b-instruct-q4_K_M",
    "llama3.1:8b-instruct-q4_K_M",
]


def new_hard_prompts():
    """sec-bh-019 and above — the v2 expansion."""
    out = []
    for p in load_security_swe():
        if p.tier == "hard" and p.id.startswith("sec-bh-"):
            try:
                num = int(p.id.rsplit("-", 1)[1])
            except ValueError:
                continue
            if num >= 19:
                out.append(p)
    return out


def dir_for(model_safe: str) -> Path | None:
    hits = sorted(_RESULTS.glob(f"*hard2-{model_safe}"))
    return hits[-1] if hits else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args(argv)

    prompts = new_hard_prompts()
    print(f"[hard2] {len(prompts)} new hard prompts, {len(MODELS)} models")

    runner = OllamaRunner(host=args.host, timeout=args.timeout)
    if not runner.is_up():
        print(f"[error] Ollama not reachable at {args.host}")
        return 2
    classifier = RefusalClassifier(mode="heuristic")   # match the main sweep

    for model in MODELS:
        safe = model.replace("/", "_").replace(":", "_").replace(".", "_")
        existing = dir_for(safe)
        if existing and (existing / "responses.jsonl").exists():
            n = sum(1 for _ in (existing / "responses.jsonl").open(encoding="utf-8"))
            if n >= len(prompts):
                print(f"[skip] {model}: already {n} rows")
                continue
        if not runner.ensure_model(model, pull=False):
            print(f"[warn] {model} not available locally; skipping")
            continue

        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = _RESULTS / f"{stamp}-hard2-{safe}"
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"[model] {model} -> {run_dir.name}")
        with (run_dir / "responses.jsonl").open("w", encoding="utf-8") as out:
            for i, pr in enumerate(prompts, 1):
                gen = runner.generate(model=model, prompt=pr.text,
                                      temperature=0.0, seed=42, num_predict=512)
                cls = classifier.classify(pr.text, gen.response)
                out.write(json.dumps({
                    "model": model, "prompt_id": pr.id, "dataset": "security_swe",
                    "gold": pr.gold, "category": pr.category,
                    "trigger_words": pr.trigger_words, "pair_id": pr.pair_id,
                    "pred": cls.label.value, "pred_source": cls.source,
                    "pred_confidence": round(cls.confidence, 3),
                    "latency_s": round(gen.latency_s, 2), "error": gen.error,
                    "response": gen.response,
                }, ensure_ascii=False) + "\n")
                out.flush()
                if i % 20 == 0 or i == len(prompts):
                    print(f"  {i}/{len(prompts)}")
    print("HARD2 DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
