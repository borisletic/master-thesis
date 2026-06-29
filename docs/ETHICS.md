# Ethics & responsible-use statement

This project **measures** safety behavior; it does not build attack tooling.

## Harmful prompts

`data/security_swe/harmful.jsonl` contains genuinely harmful *requests*. They exist
**only as negative labels** — to verify that a model retains safety (True Refusal
Rate) and to provide lexical-contrast pairs for the benign prompts. Specifically:

- They are **deliberately under-specified**: no working payloads, no real exploit
  code, no actual targets (example hostnames use RFC-5737/RFC-2606 reserved ranges
  like `198.51.100.x`, `example.com`).
- The benign set is the contribution; the harmful set is a control.

### Retention of model outputs (committed to this public repository)

For **full reproducibility and auditability** of the safety evaluation, complete
model outputs are retained in `results/` and committed — including the responses to
harmful-control prompts. We made this an explicit choice because the value of the
True-Refusal-Rate and classifier-validation results depends on the actual responses
being inspectable; reporting only the labels would make the safety numbers
unverifiable.

We judge the residual risk to be low and outweighed by that reproducibility value:

- The harmful prompts are deliberately under-specified (no real targets, no working
  payloads), so the responses are not targeted operational attack artifacts.
- The outputs come from small, openly-available local models (≤9B); they contain no
  novel capability beyond what those public models already produce on demand.
- Most harmful-prompt responses are refusals or disclaimer-heavy partial answers; a
  minority (chiefly from the weakly-aligned `mistral` and the small `phi-3.5`) are
  genuine compliances — these are exactly the safety failures the study measures.

This repository is **public**; the retention is therefore a deliberate transparency
decision, not an oversight. Anyone reusing or forking the data should be aware that
`results/*/responses*.jsonl` and `results/validation_sample.csv` contain unfiltered
model outputs, some of which are harmful-by-construction.

## Benign prompts

Built from public, openly-licensed material: CWE/CVE descriptions
(cwe.mitre.org / nvd.nist.gov), defensive and CTF write-ups, StackOverflow-style
developer questions, and synthetic log snippets. Provenance is recorded per item
(`source`). Verify each third-party source's license before redistribution.

## Third-party datasets

XSTest (CC BY 4.0) and OR-Bench are downloaded, not redistributed here, and used
under their stated licenses. Cite the original papers.

## Models

The evaluated models are all standard instruct/aligned releases
(qwen2.5-7B-Instruct, llama3.1-8B-Instruct, gemma2-9B-Instruct, phi-3.5-mini), with
**mistral-7B** serving as the weakly-aligned contrast for the alignment-tax analysis
(RQ2). No "uncensored"/abliterated models were used. The weakly-aligned baseline is
evaluated to *measure* the alignment tax, not recommended for deployment; the
deployment recommendation is the well-balanced qwen2.5-7B-Instruct.

## Intended use

The output is an empirical basis for choosing models, quantization levels, and
prompting strategies for **defensive**, on-premise security/SWE assistance under
data-privacy constraints (GDPR/DSGVO). It is not intended to facilitate misuse.
