"""Run the over-refusal experiment for one or more models × datasets.

For each (model, prompt): generate a response, classify it as
refusal/partial/compliance, and write a row to a JSONL results file. A run
manifest records the configuration for reproducibility.

Examples
--------
    # smoke test on 5 prompts, one model
    python -m scripts.run_experiment --models qwen2.5:7b-instruct-q4_K_M \
        --datasets security_swe --limit 5

    # full run over two datasets, multiple models
    python -m scripts.run_experiment \
        --models qwen2.5:7b-instruct-q4_K_M llama3.1:8b-instruct-q4_K_M \
        --datasets security_swe xstest

    # dry run: build the prompt plan without calling the model
    python -m scripts.run_experiment --models X --datasets security_swe --dry-run
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401  (sys.path shim; -m scripts.x)
except ImportError:
    import _bootstrap  # noqa: F401  (direct file run)

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from orr.classification import RefusalClassifier
from orr.datasets import load_dataset
from orr.inference import OllamaRunner

_REPO = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", required=True, help="Ollama model tags")
    p.add_argument("--datasets", nargs="+", default=["security_swe"], help="dataset keys")
    p.add_argument("--limit", type=int, default=None, help="cap prompts per dataset")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--num-predict", type=int, default=512)
    p.add_argument("--host", default="http://localhost:11434")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--system-prompt", default=None, help="optional system prompt for the model under test")
    p.add_argument("--classify", choices=["heuristic", "hybrid"], default="hybrid")
    p.add_argument("--judge-model", default=None, help="model for LLM-judge fallback (defaults to first --models entry)")
    p.add_argument("--output-dir", default=str(_REPO / "results"))
    p.add_argument("--tag", default=None, help="human label for this run dir")
    p.add_argument("--pull", action="store_true", help="ollama pull missing models")
    p.add_argument("--dry-run", action="store_true", help="build plan, don't call the model")
    return p.parse_args(argv)


def make_run_dir(output_dir: Path, tag: str | None) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}-{tag}" if tag else stamp
    run_dir = output_dir / name
    run_dir.mkdir(parents=True, exist_ok=True)
    # convenience symlink/copy pointer
    latest = output_dir / "latest"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(run_dir.name, target_is_directory=True)
    except (OSError, NotImplementedError):
        (output_dir / "LATEST.txt").write_text(run_dir.name, encoding="utf-8")
    return run_dir


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    run_dir = make_run_dir(output_dir, args.tag)

    # build prompt plan
    plan: list = []
    for ds in args.datasets:
        prompts = load_dataset(ds, limit=args.limit)
        if not prompts:
            print(f"[warn] dataset {ds!r} returned 0 prompts (not downloaded yet?)", file=sys.stderr)
        plan.extend(prompts)

    manifest = {
        "created": dt.datetime.now().isoformat(),
        "models": args.models,
        "datasets": args.datasets,
        "limit": args.limit,
        "temperature": args.temperature,
        "seed": args.seed,
        "num_predict": args.num_predict,
        "classify": args.classify,
        "system_prompt": args.system_prompt,
        "n_prompts_per_model": len(plan),
        "total_generations": len(plan) * len(args.models),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[run] {run_dir}")
    print(f"[run] {len(plan)} prompts × {len(args.models)} models = {len(plan) * len(args.models)} generations")

    if args.dry_run:
        print("[dry-run] plan built; not calling models.")
        for pr in plan[:10]:
            print(f"  - [{pr.dataset}/{pr.gold}] {pr.id}: {pr.text[:70]}...")
        return 0

    runner = OllamaRunner(host=args.host, timeout=args.timeout, system_prompt=args.system_prompt)
    if not runner.is_up():
        print(f"[error] Ollama not reachable at {args.host}. Start it with `ollama serve`.", file=sys.stderr)
        return 2

    judge_model = args.judge_model or args.models[0]
    classifier = RefusalClassifier(
        runner=runner,
        judge_model=judge_model,
        mode=args.classify,
    )

    results_path = run_dir / "responses.jsonl"
    n_done = 0
    with results_path.open("w", encoding="utf-8") as out:
        for model in args.models:
            if not runner.ensure_model(model, pull=args.pull):
                print(f"[error] model {model!r} not available locally (use --pull). Skipping.", file=sys.stderr)
                continue
            print(f"[model] {model}")
            for i, pr in enumerate(plan, 1):
                gen = runner.generate(
                    model=model,
                    prompt=pr.text,
                    temperature=args.temperature,
                    seed=args.seed,
                    num_predict=args.num_predict,
                )
                cls = classifier.classify(pr.text, gen.response)
                row = {
                    "model": model,
                    "prompt_id": pr.id,
                    "dataset": pr.dataset,
                    "gold": pr.gold,
                    "category": pr.category,
                    "trigger_words": pr.trigger_words,
                    "pair_id": pr.pair_id,
                    "pred": cls.label.value,
                    "pred_source": cls.source,
                    "pred_confidence": round(cls.confidence, 3),
                    "latency_s": round(gen.latency_s, 2),
                    "error": gen.error,
                    "response": gen.response,
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                n_done += 1
                if i % 10 == 0 or i == len(plan):
                    print(f"  {i}/{len(plan)} ({cls.label.value})")

    print(f"[done] {n_done} generations -> {results_path}")
    print(f"[next] python -m scripts.analyze_results {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
