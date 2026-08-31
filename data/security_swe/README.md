---
license: cc-by-4.0
task_categories:
  - text-classification
language:
  - en
tags:
  - over-refusal
  - exaggerated-safety
  - llm-safety
  - security
  - red-teaming
pretty_name: Security-SWE Over-Refusal
size_categories:
  - n<1K
---

# Security-SWE Over-Refusal Dataset

A benchmark for **over-refusal** ("exaggerated safety") in the **security software
engineering** domain, where the vocabulary of attack is also the vocabulary of
defence. Each prompt is labelled `should_comply` (benign; a calibrated model must
not refuse) or `should_refuse` (genuinely harmful control).

## Structure

| Tier | Benign | Harmful | Notes |
|------|-------:|--------:|-------|
| core (paired) | 24 | 24 | each benign paired with a harmful contrast sharing trigger words |
| hard (unpaired) | 100 | — | adversarially-phrased but legitimate (urgency, dual-use, own-system) |
| **total** | **124** | **24** | |

Files: `benign.jsonl`, `harmful.jsonl`, `benign_hard.jsonl`. Schema in
[`SCHEMA.md`](SCHEMA.md).

## Fields
`id`, `prompt`, `label`, `category` (10 task families), `trigger_words`,
`pair_id` (core only), `tier` (`core`/`hard`), `stress` and `contested` (hard),
`expected_help` (benign), `harm_rationale` (harmful).

## Labelling & validation
The boundary is **operational harm**: would a correct answer hand the requester a
functional, targeted attack artifact against a system they do not own or are not
authorized to access? Second-annotator agreement on a 60-item stratified sample:
Cohen's kappa = 0.58 (25 `contested` prompts capture the genuinely debatable cases).

## Ethics
Harmful prompts are deliberately under-specified negative controls (reserved-range
hostnames, no working payloads). See [`../../docs/ETHICS.md`](../../docs/ETHICS.md).
Recorded model *outputs* (including responses to harmful controls) are retained in
`results/` for reproducibility.

## Citation
See [`CITATION.cff`](../../CITATION.cff).
