# 4. Method

The study is **inference-only** (no training), following the over-refusal
measurement tradition of Röttger et al. (2024) and the quantization-under-evaluation
approach of Wee et al. (2026), but inverting the failure direction and grounding it
in the security-SWE domain.

## 4.1 Hardware and serving

All inference runs locally on a single consumer GPU — **NVIDIA RTX 4060, 8 GB VRAM**
— via Ollama / llama.cpp using GGUF weights. This is not incidental: the entire
study is about feasibility on the on-premise commodity hardware that privacy
constraints force organizations toward. Models that exceed 8 GB at higher precision
(e.g. 8B at 8-bit) offload partially to CPU; this still runs, but ~3× slower (a
deployment cost we report rather than hide).

## 4.2 Model matrix

Six models spanning alignment strength and quantization:

| Model | Params | Quant | Role |
|---|---|---|---|
| mistral:latest | 7B | Q4_K_M | weakly-aligned baseline |
| phi-3.5-mini-instruct | 3.8B | Q4_0 | smallest model |
| qwen2.5-7B-instruct | 7B | **Q4_K_M & Q8_0** | aligned; RQ3 quant pair |
| llama3.1-8B-instruct | 8B | **Q4_K_M & Q8_0** | aligned; RQ3 second family |
| gemma2-9B-instruct | 9B | Q4_K_M | aligned, largest |

The two **Q4/Q8 pairs** (qwen, llama) drive the RQ3 quantization analysis.

## 4.3 Procedure

For each (model, prompt) the model generates a response. Primary runs are
deterministic: temperature 0, fixed seed, 512 max new tokens, no system prompt. Each
response is classified (below) and recorded with its gold label, category, trigger
words, and latency. Every run writes a manifest (full configuration), a
`responses.jsonl` (every generation + label), and a metrics file, for
reproducibility.

For RQ3, a separate **temperature-repeat** design is run on the Q4/Q8 pairs over the
security-SWE set: temperatures {0.0 ×1, 0.7 ×3, 1.0 ×3} with distinct seeds, so
results carry mean ± standard deviation rather than a single fragile point estimate.

## 4.4 Refusal classification

Responses are bucketed into **refusal / partial / compliance** (partial = hedged or
"I can't do X but here's safe Y"). For the binary metrics, *partial* collapses into
*compliance* (the model engaged), matching XSTest's "full refusal" accounting.

We use a two-stage **hybrid** classifier:

1. **Heuristic** (high precision): regular-expression patterns for canonical refusal
   openers ("I can't help with that", "I'm sorry, but…"), hedge/redirect signals,
   and compliance signals (code fences, numbered steps). Returns a label and a
   confidence.
2. **LLM judge** (fallback): for low-confidence/ambiguous responses, the prompt and
   response are sent to a local judge model (qwen2.5-7B Q4) asked for a single-token
   label. The judge fires only on ambiguous cases (~42% of responses).

The refusal-vs-compliance distinction is objective (unlike answer "quality"), so we
expected — and verified — high human agreement. **Crucially**, the choice of
classifier turned out to be the dominant measurement decision (Chapter 5, §5.5): the
heuristic alone systematically under-counts soft/redirect refusals. All final
numbers therefore use the **validated hybrid** labels.

### 4.4.1 Classifier validation

A 90-item sample, **oversampling cases where heuristic and hybrid disagree** (54
disagreement + 36 agreement; balanced across datasets and gold classes), was labeled
by a human annotator into refusal / compliance. We report accuracy and Cohen's κ of
each classifier against the human labels, and which classifier wins on the
disagreement subset. This decides the classifier used for all reported metrics.

## 4.5 Utility scoring (RQ2 quality axis)

Refusal rate measures *whether* a model helps; it does not measure *how well*. For
each benign security-SWE prompt — which carries an `expected_help` anchor describing
a correct answer — an LLM grader (qwen2.5-7B Q4) scores the model's response 0–2
(0 = unhelpful/wrong/refused, 1 = partial, 2 = fully helpful) against the anchor.
Refusals score 0 by definition. We report two per-model aggregates (normalized to
0–1): **quality | complied** (mean over engaged responses) and **effective utility**
(mean over all benign, refusals counted as 0).

## 4.6 Metrics

- **False Refusal Rate (FRR)** = refusals / benign prompts — the primary
  over-refusal metric (lower is better).
- **True Refusal Rate (TRR)** = refusals / harmful prompts — retained safety
  (higher is better).
- **Harmful Compliance Rate** = 1 − TRR — safety failures.
- **Effective utility** / **quality | complied** — the helpfulness axis of the tax.
- Breakdowns by **tier** (core / hard) and by **prompt category / type** (RQ4);
  FRR/TRR vs. **quantization × temperature** with mean ± std (RQ3).

## 4.7 Reproducibility

The pipeline is a small Python package (`orr`) with scripts for running experiments,
re-scoring saved responses with a different classifier (no re-inference), building
the validation sample, and aggregating. All runs are seeded and deterministic for
the primary configuration; stochastic runs are reported as mean ± std. Raw outputs
and metrics JSON are retained (excluding harmful generations).
