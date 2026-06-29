# Evaluating Over-Refusal and the Alignment–Utility Trade-off in Small Local Language Models

Master thesis project (FTN). Systematic evaluation of **over-refusal** ("exaggerated
safety") in small, locally-deployable, quantized language models, focused on the
**security software-engineering domain**, where legitimate work is full of
"dangerous-sounding" vocabulary (attack, exploit, payload, inject, kill, reverse
shell, malware analysis).

The study is **inference-only** (no training). It measures, across a matrix of
models × alignment-variants × quantization-levels:

- **RQ1** — How severe is over-refusal (false-refusal rate) on benign security-SWE
  tasks vs. general benchmarks (XSTest / OR-Bench)?
- **RQ2** — The *alignment tax*: how much utility on legitimate security tasks is
  sacrificed by alignment (aligned vs. base/uncensored), and is the tax "justified"
  (does more benign refusal correlate with better harmful refusal)?
- **RQ3** — Does quantization (FP16 → INT8 → INT4) shift over-refusal of benign
  tasks, and in which direction? (Prior work studies quantization × *harmful
  compliance*; the benign-refusal direction is unexplored.)
- **RQ4** (optional) — Which trigger words/topics drive lexical over-refusal — is
  the failure lexical or contextual?

## Repository layout

```
master-thesis/
├── config/                 # experiment + model-matrix configuration
│   └── models.yaml
├── data/
│   ├── security_swe/       # OWN dataset (main contribution): benign + harmful pairs
│   ├── xstest/             # downloaded (Röttger et al. 2024)
│   └── or_bench/           # downloaded (Cui et al. 2024)
├── src/orr/                # python package ("over-refusal research")
│   ├── datasets/           # dataset loaders + schema
│   ├── inference/          # Ollama runner
│   ├── classification/     # refusal detection (heuristics + LLM judge)
│   └── evaluation/         # metrics (FRR, compliance, alignment tax)
├── scripts/                # CLI entry points (download, run, analyze)
├── results/                # committed run outputs (manifests, responses, metrics)
├── docs/                   # thesis text (docs/thesis/), methodology, findings
└── tests/
```

## Quick start

```bash
# 1. install deps (Python 3.11+ recommended; see note in requirements.txt)
pip install -r requirements.txt

# 2. start Ollama and pull a model
ollama serve            # in a separate terminal
ollama pull qwen2.5:7b-instruct-q4_K_M

# 3. smoke-test the pipeline on the own dataset, one model
python -m scripts.run_experiment --models qwen2.5:7b-instruct-q4_K_M \
    --datasets security_swe --limit 5

# 4. analyze a single run
python -m scripts.analyze_results results/latest

# --- reproduce / inspect the full study ---
# re-run the 6-model sweep (resumable, ~hours on an 8GB GPU)
bash scripts/run_sweep.sh
# re-score saved responses with the validated hybrid classifier
python -m scripts.reclassify --glob '*sweep*'
# the validated cross-model tables (RQ1/RQ2/RQ4)
python -m scripts.aggregate_sweep --glob '2026*sweep*' \
    --responses-name responses_hybrid.jsonl --by-tier --by-xstest-type
```

The committed [`results/`](results/) already contain every run's outputs and
`sweep_hybrid_metrics.json`, so the tables can be regenerated without re-running
inference.

## Hardware target

Single consumer GPU (**RTX 4060, 8 GB VRAM**). The whole study is about feasibility
on on-premise consumer hardware — the motivation for local/quantized inference is
data privacy (GDPR/DSGVO): business-sensitive code must not leave the premises.

## Status

**Experiments complete.** Six models evaluated on XSTest + the Security-SWE set,
with a human-validated refusal classifier (Cohen's κ = 0.72); RQ1–RQ4 answered.
Results live in [`results/`](results/) (per-run `responses*.jsonl` + `metrics.json`,
plus `sweep_hybrid_metrics.json`); the thesis draft is in
[`docs/thesis/`](docs/thesis/README.md). Findings log: [docs/FINDINGS.md](docs/FINDINGS.md);
build history: [docs/PROGRESS.md](docs/PROGRESS.md).

### Headline result (security-SWE, validated)

| Model | over-refusal (FRR hard) | safety (TRR) | effective utility |
|---|---:|---:|---:|
| mistral-7B | 0.0% | 41.7% | 0.94 |
| phi-3.5-mini | 11.1% | 20.8% | 0.71 |
| qwen2.5-7B Q4 | 5.6% | 79.2% | 0.90 |
| qwen2.5-7B Q8 | 5.6% | 91.7% | 0.93 |
| gemma2-9B | 55.6% | 100% | 0.71 |
| llama3.1-8B | 72.2% | 100% | 0.63 |

**Recommendation:** qwen2.5-7B-Instruct (4-bit) — best joint over-refusal / safety /
utility on 8 GB on-premise hardware.

## License & ethics

The own dataset is built from public sources (CWE/CVE descriptions, defensive/CTF
write-ups, StackOverflow-style dev questions, log snippets). Harmful "control"
prompts are included **only** as negative labels to verify that models retain safety.
For reproducibility this public repo **retains full model outputs** in `results/`,
including responses to harmful-control prompts (produced by small local models from
deliberately under-specified prompts). Anyone reusing the data should read
[docs/ETHICS.md](docs/ETHICS.md) — `results/*/responses*.jsonl` contain unfiltered,
harmful-by-construction outputs.
