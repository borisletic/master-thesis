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
├── results/                # generated outputs (git-ignored)
├── docs/                   # thesis text, methodology notes
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

# 4. analyze
python -m scripts.analyze_results results/latest
```

## Hardware target

Single consumer GPU (**RTX 4060, 8 GB VRAM**). The whole study is about feasibility
on on-premise consumer hardware — the motivation for local/quantized inference is
data privacy (GDPR/DSGVO): business-sensitive code must not leave the premises.

## Status

See [docs/PROGRESS.md](docs/PROGRESS.md) for the current build status and next steps.

## License & ethics

The own dataset is built from public sources (CWE/CVE descriptions, defensive/CTF
write-ups, StackOverflow-style dev questions, log snippets). Harmful "control"
prompts are included **only** as negative labels to verify that models retain
safety; no functional harmful artifacts are produced or stored. See
[docs/ETHICS.md](docs/ETHICS.md).
