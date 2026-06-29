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

## Milestone (2026-06-29): all 4 RQs answered + thesis draft written

- 6-model sweep (XSTest + security-SWE) complete; **hybrid classifier human-validated
  (κ=0.716, 86.7% acc)** → all numbers use hybrid (`responses_hybrid.jsonl`).
- **RQ1** domain vs general; **RQ2** alignment–utility trade-off + utility scoring
  (tax paid via refusal not quality); **RQ3** quantization within sampling noise,
  replicated on qwen AND llama; **RQ4** over-refusal contextual not lexical.
- **Thesis draft written**: English Markdown, 8 chapters + refs (~6k words) in
  `docs/thesis/` — see [thesis/README.md](thesis/README.md).
- Remaining: thesis revision/polish; optional (2nd grader, OR-Bench at scale,
  inter-annotator κ); convert to .docx when content settled. **Not yet committed.**

## First result (see docs/FINDINGS.md)

- Pipeline validated end-to-end on `mistral:latest` over the full security_swe set.
- **FRR = 0%** (no over-refusal) but **TRR = 29%** — mistral is a helpful-but-under-
  aligned baseline. Surfaced a key methodological point: refuse-then-redirect
  responses need the 3-way label + human adjudication (the 70.8% harmful-compliance
  is an upper bound).

## Next (in rough priority order)

1. ~~Bring up Ollama + first model; first real run.~~ ✅ done (mistral baseline).
2. ~~Add aligned model (qwen2.5:7b-instruct); compare to mistral.~~ ✅ done —
   qwen FRR 0% / TRR 75% vs mistral 0% / 29% (no alignment tax on this set).
3. ~~Download XSTest for the general baseline.~~ ✅ done (fixed an "unsafe"→safe
   substring bug in the loader; regression-tested). **qwen×XSTest run in progress**
   to get a calibrated FRR (the domain set gave 0%, so XSTest is the control that
   should reveal whether qwen over-refuses at all).
4. ~~Harden the benign set~~ ✅ added an 18-prompt **hard tier** (`benign_hard.jsonl`,
   `tier:hard`, unpaired): urgency/authority pressure, attacker-roleplay-for-defense,
   own-system, sanctioned red-team, real-payloads-for-defensive-testing. Dataset now
   66 prompts (48 core + 18 hard). Run models against the hard tier next to get a
   non-zero FRR.
5. ~~Pull standard model set~~ ✅ 6 models: mistral, qwen2.5-7b-instruct (q4+q8),
   llama3.1-8b-instruct, gemma2-9b-instruct, phi3.5.
   **Cross-model + RQ3 sweep RUNNING** via `scripts/run_sweep.sh` (resumable,
   heuristic classify, per-model dirs `results/*-sweep-<model>`, ~4-6 h).
   Aggregate with `python -m scripts.aggregate_sweep --by-tier --by-xstest-type`.

   ### Sweep ops protocol (the run gets killed at session boundaries — resume safely)
   `scripts/run_sweep.sh` is **idempotent**: it SKIPS any model whose dir already
   has 516 rows and re-runs partials. To resume after an interruption:
   1. **FIRST check for live workers** (a "stopped" notification can be a FALSE
      alarm — the process may still be running):
      `powershell "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -like '*run_experiment*' }"`
   2. If a worker is alive → do NOT relaunch (would duplicate + thrash the GPU); wait.
   3. If none alive and not all 6 dirs are complete → `bash scripts/run_sweep.sh` again.
   4. **SWEEP COMPLETE** ✅ all 6 models (mistral, llama3.1, gemma2, phi3.5,
      qwen Q4, qwen Q8) at 516/516. Results in `results/sweep_combined_metrics.json`
      and `docs/FINDINGS.md` (2026-06-29 full sweep). Central result: visible
      alignment-utility trade-off on the hard tier; over-refusal is contextual not
      lexical. **Top next task: human-validate classifier + hybrid re-score** (the
      heuristic under-counts contextual refusals — see classifier caveat).
6. **Classifier validation** — export a 60-row human-label sample, fill it,
   score agreement + Cohen's κ (target κ > 0.8). Tune patterns if needed.
7. **Decide OR-Bench split** for the scale baseline.
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
