# Progress & build status

_Last updated: 2026-06-28_

## Done

- [x] Repository scaffold (package `src/orr`, scripts, tests, config, docs).
- [x] **Inference layer** — `OllamaRunner` over the Ollama HTTP API (`requests` only).
- [x] **Refusal classifier** — rule-based heuristics (`refusal_heuristics.py`) +
      hybrid LLM-judge fallback (`classifier.py`), 3-way labels
      (refusal/partial/compliance).
- [x] **Metrics** — FRR, safe-compliance, true-refusal, harmful-compliance,
      trigger-word breakdown, mean±std (`evaluation/metrics.py`).
- [x] **Own dataset v0** — `data/security_swe/`: 24 benign + 24 harmful **paired**
      prompts across 10 categories, with schema + ethics notes.
- [x] **Dataset loaders** — security_swe (own), xstest, or_bench unified into `Prompt`.
- [x] **Pipeline scripts** — `run_experiment`, `analyze_results`,
      `download_datasets`, `validate_classifier`.
- [x] **Tests** — 13 passing (heuristics, metrics, dataset integrity); no GPU needed.

## Next (in rough priority order)

1. **Bring up Ollama + first model.** `ollama serve`; pull
   `qwen2.5:7b-instruct-q4_K_M`; run the smoke test (5 prompts) end-to-end.
2. **First real run** — security_swe, one model, FP16/Q8/Q4 if they fit 8 GB;
   inspect responses + metrics; sanity-check the heuristic on real outputs.
3. **Classifier validation** — export a 60-row human-label sample, fill it,
   score agreement + Cohen's κ (target κ > 0.8). Tune patterns if needed.
4. **Download XSTest** (and decide on OR-Bench split) for the general baseline.
5. **Grow the own dataset** toward ~100+ pairs; add a second annotator and report κ.
6. **Model matrix runs** — aligned vs uncensored (RQ2); FP16→Q8→Q4 sweep (RQ3).
7. **Stochastic robustness** — temperature sweep, report mean±std.
8. **Analysis/plots** — FRR-vs-quantization curves; trigger-word ranking (RQ4);
   alignment-tax scatter (benign-refusal vs harmful-refusal).
9. **Thesis write-up** in `docs/thesis/`.

## Open decisions

- Which exact "uncensored/abliterated" model is the fairest base contrast (RQ2)?
- OR-Bench split: hard-1k vs the full 80k (cost vs coverage).
- Utility scoring for RQ2: rubric-based LLM grader vs manual rubric on a subsample.
- Whether to add a system-prompt arm (XSTest showed system prompts flip behavior).
