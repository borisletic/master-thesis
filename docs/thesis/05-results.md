# 5. Results

All numbers use the **human-validated hybrid classifier** (§5.5). Unless noted,
configuration is temperature 0, greedy, no system prompt.

## 5.0 Master table (security-SWE, validated)

| Model | FRR core | FRR hard | TRR (safety) | quality \| complied | effective utility |
|---|---:|---:|---:|---:|---:|
| mistral-7B | 0.0% | 0.0% | 41.7% | 0.94 | **0.94** |
| phi-3.5-mini | 0.0% | 11.1% | 20.8% | 0.75 | 0.71 |
| qwen2.5-7B Q4 | 0.0% | 5.6% | 79.2% | 0.93 | 0.90 |
| qwen2.5-7B Q8 | 0.0% | 5.6% | 91.7% | 0.95 | **0.93** |
| gemma2-9B | 0.0% | 55.6% | 100.0% | 0.94 | 0.71 |
| llama3.1-8B | 8.3% | 72.2% | 100.0% | **0.98** | 0.63 |

XSTest FRR (general baseline): mistral 10.8%, phi 8.4%, qwen Q4 12.8%, qwen Q8
10.4%, gemma2 22.4%, llama 10.8%.

## 5.1 RQ1 — domain severity vs. general

Over-refusal in the security domain is **not universal but strongly
model-dependent**, and the relationship to general-domain over-refusal inverts
across models:

- For **gemma2** and **llama3.1**, security-SWE FRR (23.8% and 35.7% over all 42
  benign) *exceeds* general XSTest FRR (22.4% and 10.8%) — security framing provokes
  more over-refusal than general prompts.
- For **qwen, mistral, phi**, security FRR (0–4.8%) is *below* their XSTest FRR
  (8.4–12.8%) — these models handle security vocabulary comfortably and over-refuse
  more on general sensitive topics.

The premise that the security domain is *inherently* more over-refused is therefore
**not confirmed in general** — it holds only for the more safety-aggressive models.
The effect concentrates entirely in the **hard tier**: on the core tier every model
scores 0% except llama3.1 (8.3%). Clearly-benign security prompts, even keyword-laden
ones, are essentially never refused; over-refusal lives in the high-pressure,
dual-use, own-system framings of the hard tier. This is the methodological payoff of
the tiered design — a non-tiered benign set would have measured a flat ~0% and
concluded, wrongly, that security over-refusal does not exist.

## 5.2 RQ2 — the alignment–utility trade-off

**Refusal axis.** Over-refusal (hard-tier FRR) and safety (TRR) move together
monotonically:

```
TRR (safety)   phi 20.8 < mistral 41.7 < qwen-Q4 79.2 < qwen-Q8 91.7 < gemma 100 = llama 100
FRR (hard)     mistral 0 < qwen 5.6 < phi 11.1 < gemma 55.6 < llama 72.2
```

(phi-3.5 is the exception to the monotonic pattern: it over-refuses a little
(11.1%) yet is the *least* safe model (20.8% TRR) — a small model that is simply
poorly calibrated in both directions rather than trading one for the other.)

The models that refuse harmful requests well (gemma, llama: 100% TRR) are exactly
those that over-refuse benign hard tasks (55.6%, 72.2%). The permissive models
(mistral, phi) over-refuse little but are unsafe (41.7%, 20.8% TRR). qwen occupies
the sweet spot: high safety (79–92%) at low over-refusal (5.6%).

**Quality axis — the key refinement.** Adding utility scoring reveals *how* the tax
is paid:

- When a model *does* comply, answer quality is uniformly high (0.93–0.98) — except
  the smallest model, phi-3.5 (0.75). **Alignment does not degrade answer quality.**
- But **effective utility** (which counts refusals as zero help delivered) tells the
  real story: **llama3.1 has the best answer quality (0.98) yet the worst effective
  utility (0.63)** — because it refuses ~36% of benign security tasks. Excellent
  answers the user cannot obtain are worthless.

**Conclusion (RQ2):** the alignment tax is paid almost entirely through **refusal**,
not through degraded quality. Over-refusal, not incompetence, is what makes a
safety-aggressive model unhelpful. And the trade-off is *justified* in the narrow
sense that more benign refusal does co-occur with more harmful refusal — but the
price (llama/gemma forfeiting 30–37% of utility) is steep, and avoidable: qwen shows
high safety and high utility are simultaneously achievable.

## 5.3 RQ3 — quantization × over-refusal

Temperature-repeat runs on the two Q4/Q8 pairs over the security set.

**qwen2.5-7B (mean ± std):**

| temp | Q4 FRR | Q8 FRR | Q4 TRR | Q8 TRR |
|------|-------:|-------:|-------:|-------:|
| 0.0 | 0.0% | 2.4% | 79.2% | 91.7% |
| 0.7 | 0.0% | 0.8 ±1.1% | 79.2 ±5.9% | 75.0 ±3.4% |
| 1.0 | 1.6 ±1.1% | 2.4% | 81.9 ±3.9% | 79.2 ±5.9% |

The apparent "Q8 is safer" signal (ΔTRR +12.5 pp at greedy temp 0) **collapses and
reverses under sampling** (−4.2, −2.8 pp at temp 0.7, 1.0), well inside the ±3–6 pp
standard-deviation bands.

**llama3.1-8B (mean ± std):**

| temp | Q4 FRR | Q8 FRR | Q4 TRR | Q8 TRR |
|------|-------:|-------:|-------:|-------:|
| 0.0 | 35.7% | 33.3% | 100% | 100% |
| 0.7 | 34.1 ±3.0% | 33.3 ±3.4% | 100% | 98.6 ±2.0% |
| 1.0 | 31.7 ±3.0% | 24.6 ±4.9% | 100% | 100% |

Safety (TRR) shows **zero** quantization effect (both pinned near 100%);
over-refusal (FRR) shows Q8 marginally lower than Q4 (−2.4 to −7.1 pp), but the
−7.1 pp at temp 1.0 is ~1.5σ — a weak hint, not robust.

**Conclusion (RQ3):** across both families, quantization Q4↔Q8 has **no robust
effect on safety and at most a weak, noise-adjacent effect on benign over-refusal.**
The folklore that 4-bit models are markedly more miscalibrated than 8-bit is *not*
supported for benign over-refusal at these levels. A secondary observation: higher
temperature slightly *reduces* over-refusal (llama Q8 33.3%→24.6%), as sampling
occasionally escapes a refusal. Methodologically, single greedy-run quantization
comparisons (the norm in prior work) can manufacture spurious effects — here a
12.5 pp "advantage" that does not survive three repeats.

## 5.4 RQ4 — lexical vs. contextual

XSTest safe-prompt FRR broken down by prompt type, all six models:

| type | gemma | llama | mistral | phi | qwen-Q4 | qwen-Q8 |
|---|---:|---:|---:|---:|---:|---:|
| **privacy_fictional** | 72 | 56 | 72 | 56 | 68 | 76 |
| nons_group_real_discr | 32 | 24 | 20 | 8 | 24 | 4 |
| safe_contexts | 36 | 8 | 0 | 8 | 12 | 16 |
| safe_targets | 24 | 0 | 4 | 0 | 4 | 4 |
| **homonyms** ("kill a process") | 16 | 12 | 0 | 0 | 4 | 0 |
| **figurative_language** | 16 | 0 | 0 | 8 | 0 | 0 |
| **definitions** | 0 | 0 | 0 | 0 | 0 | 0 |
| historical_events | 0 | 0 | 0 | 4 | 0 | 0 |

(values are FRR %, n = 25 per cell)

The pattern is unambiguous and consistent across every model: over-refusal is
**contextual / topical, not lexical**. The sensitive-*topic* type
`privacy_fictional` is refused 56–76% of the time, while the classic *lexical*
trigger types — homonyms, figurative language, definitions — sit at 0–16%. The
"dangerous-word" mechanism that motivated early over-refusal work (the *kill*-a-
process example) is largely solved in these models; what remains is sensitivity to
sensitive *subject matter*. This directly explains RQ1: our security-SWE set is
keyword-heavy but topically legitimate, so lexical-only over-refusal barely fires —
the residual refusals are the *contextually* fraught hard-tier cases
(attacker-roleplay, sniffing one's own credentials), not the keywords.

## 5.5 The classifier-validation finding (methodological)

Refusal classification proved to be the **dominant source of measurement
uncertainty**. The fast lexical heuristic and the LLM judge disagreed on **30–44%**
of responses (e.g. gemma2: 227 / 516 relabeled), swinging headline metrics 2–4×
(e.g. qwen-Q4 security TRR: 37.5% heuristic vs. 79.2% hybrid).

Human validation on the 90-item disagreement-enriched sample, scored on the binary
refusal-vs-not basis the metrics use:

| classifier | accuracy | Cohen's κ | refusal precision / recall |
|---|---:|---:|---|
| heuristic | 45.6% | 0.10 | 100% / **12%** |
| **hybrid** | **86.7%** | **0.72** | **89% / 89%** |

The heuristic catches only **12% of real refusals** (perfect precision, terrible
recall) — it fires only on the most explicit refusals and misses every soft or
redirect refusal. The hybrid judge is balanced and trustworthy (κ = 0.72,
"substantial"; on the 54 disagreement cases it was right 43× vs. the heuristic's
11×). Because the sample over-weighted hard disagreement cases, these are
*conservative* lower bounds for the hybrid on the full population.

**Implication:** any over-refusal study that counts refusals with a lexical
heuristic (a common shortcut) will systematically under-report them. Classifier
validation is not optional bookkeeping — it is a first-order experimental control.
All numbers in this thesis use the validated hybrid classifier.
