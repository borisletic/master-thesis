# Methodology

Inference-only evaluation (no training), following the over-refusal measurement
tradition of Röttger et al. (2024, XSTest) and the quantization×safety evaluation
of Wee et al. (2026), but inverting the failure direction (benign over-refusal,
not harmful compliance) and grounding it in the **security software-engineering**
domain.

## 1. Model matrix

Two crossed factors (see `config/models.yaml`):

- **Alignment** (RQ2): aligned/instruct models vs. their base / "uncensored"
  (abliterated) variants — to measure the *alignment tax*.
- **Quantization** (RQ3): FP16 → INT8 (Q8_0) → INT4 (Q4_K_M) per model.

All inference is local via Ollama / llama.cpp (GGUF) on a single **RTX 4060 (8 GB)**.
Models that exceed 8 GB at higher precision offload partially to CPU (slower, still
valid). VRAM estimates are recorded per variant.

## 2. Procedure

For each `(model, quantization, prompt)`:

1. Generate a response (greedy, `temperature=0`, fixed `seed`, `num_predict=512`)
   for the primary runs.
2. Classify the response as **refusal / partial / compliance**.
3. Record gold label (`should_comply` benign / `should_refuse` harmful), prediction,
   trigger words, category, latency.

A separate **stochastic-robustness** pass repeats a subset at
`temperature ∈ {0.0, 0.7, 1.0}` and reports **mean ± std** to account for sampling.

## 3. Refusal classification

Two-stage **hybrid** classifier (`src/orr/classification`):

- **Heuristic** (high precision): regex patterns for canonical refusal openers
  ("I can't help with that", "I'm sorry, but…"), partial/hedge signals
  ("I can't X, but I can Y"), and compliance signals (code fences, numbered steps).
  Returns a label + confidence.
- **LLM judge** (fallback): for low-confidence/ambiguous cases the response is sent
  to a local judge model asked for a single-token label. (A cloud model can serve
  as a tie-break/ceiling.)

The refusal-vs-compliance distinction is *objective* (unlike answer "quality"), so
high agreement is expected. The classifier is **validated against human labels** on
a ≥60-item sample (`scripts/validate_classifier.py`): we report accuracy and
**Cohen's κ** (target κ > 0.8); patterns are tuned only against the validation set.

## 4. Datasets

- **Own — Security-SWE Over-Refusal** (main contribution): benign security/SWE
  prompts with "dangerous-sounding" vocabulary, each **paired** with a genuinely
  harmful contrast sharing trigger words (isolates lexical vs. contextual refusal).
  Balanced by construction. Two-level annotation: (1) `should_comply`/`should_refuse`,
  (2) utility/correctness for complied benign tasks. Inter-annotator κ reported.
- **XSTest** (Röttger et al. 2024): 250 safe + 200 unsafe contrasts — general baseline.
- **OR-Bench** (Cui et al. 2024): large benign "seemingly-toxic" set — scale baseline.

## 5. Metrics (`src/orr/evaluation/metrics.py`)

For binary refusal accounting, `partial` collapses into `compliance` (the model did
engage), matching XSTest's "full refusal" definition; the 3-way counts are retained.

- **False Refusal Rate (FRR)** = refusals / benign prompts — *primary over-refusal
  metric* (lower better).
- **Safe Compliance Rate** = 1 − FRR.
- **True Refusal Rate (TRR)** = refusals / harmful prompts — retained safety (higher
  better).
- **Harmful Compliance Rate** = 1 − TRR — safety failures.
- **Alignment tax** = drop in utility/correctness on legitimate tasks (aligned vs base).
- Breakdowns by **category** and **trigger word** (RQ4); FRR-vs-quantization curves (RQ3).

## 6. Research questions → analyses

| RQ  | Question                                              | Analysis                                                   |
|-----|-------------------------------------------------------|------------------------------------------------------------|
| RQ1 | Severity of over-refusal in security-SWE vs general   | FRR on own set vs XSTest/OR-Bench, per model               |
| RQ2 | Alignment tax + is the tax justified                  | aligned vs base: ΔFRR, Δutility, and FRR↔TRR correlation   |
| RQ3 | Does quantization shift benign over-refusal           | FRR(FP16) vs FRR(Q8) vs FRR(Q4), paired per model          |
| RQ4 | Lexical vs contextual over-refusal                    | FRR per trigger word; benign↔harmful paired-contrast gap   |

## 7. Reproducibility

Each run writes `manifest.json` (full config), `responses.jsonl` (every generation +
classification), and `metrics.json`. Deterministic primary runs (fixed seed, temp 0);
stochastic runs reported as mean ± std.
