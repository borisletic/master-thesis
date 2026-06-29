# Thesis — Evaluating Over-Refusal and the Alignment–Utility Trade-off in Small Local Language Models

Domain: security software engineering. Language: English. Draft, chapter-by-chapter
Markdown. All quantitative claims use the **human-validated hybrid classifier**
(κ = 0.72); see [docs/FINDINGS.md](../FINDINGS.md) and `results/` for raw data.

## Chapters

| # | File | Contents |
|---|------|----------|
| — | [00-abstract.md](00-abstract.md) | Abstract |
| 1 | [01-introduction.md](01-introduction.md) | Motivation, problem, RQs, contributions |
| 2 | [02-background.md](02-background.md) | XSTest, OR-Bench, quantization×safety; positioning |
| 3 | [03-dataset.md](03-dataset.md) | Security-SWE dataset: core + hard tiers, schema, ethics |
| 4 | [04-method.md](04-method.md) | Hardware, model matrix, hybrid classifier, utility scoring, metrics |
| 5 | [05-results.md](05-results.md) | RQ1–RQ4 + classifier-validation finding |
| 6 | [06-discussion.md](06-discussion.md) | Deployment, contextual over-refusal, measurement lesson, limitations |
| 7 | [07-conclusion.md](07-conclusion.md) | Summary, recommendation, future work |
| — | [references.md](references.md) | References |
| — | [OUTLINE.md](OUTLINE.md) | Original planning outline (superseded by chapters) |

## Headline results (security-SWE, validated)

| Model | FRR hard | TRR | eff. utility |
|---|---:|---:|---:|
| mistral-7B | 0.0% | 41.7% | 0.94 |
| phi-3.5-mini | 11.1% | 20.8% | 0.71 |
| qwen2.5-7B Q4 | 5.6% | 79.2% | 0.90 |
| qwen2.5-7B Q8 | 5.6% | 91.7% | 0.93 |
| gemma2-9B | 55.6% | 100% | 0.71 |
| llama3.1-8B | 72.2% | 100% | 0.63 |

**Recommendation:** qwen2.5-7B-Instruct (4-bit) — best joint over-refusal / safety /
utility on 8 GB on-premise hardware.

## To produce a single document

Concatenate in order, or convert to `.docx`/PDF:

```bash
cat 00-abstract.md 01-introduction.md 02-background.md 03-dataset.md \
    04-method.md 05-results.md 06-discussion.md 07-conclusion.md references.md \
    > ../thesis-full.md
# pandoc ../thesis-full.md -o ../thesis.docx   # optional
```
