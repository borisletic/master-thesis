# Ethics & responsible-use statement

This project **measures** safety behavior; it does not build attack tooling.

## Harmful prompts

`data/security_swe/harmful.jsonl` contains genuinely harmful *requests*. They exist
**only as negative labels** — to verify that a model retains safety (True Refusal
Rate) and to provide lexical-contrast pairs for the benign prompts. Specifically:

- They are **deliberately under-specified**: no working payloads, no real exploit
  code, no actual targets (example hostnames use RFC-5737/RFC-2606 reserved ranges
  like `198.51.100.x`, `example.com`).
- The repository **never commits harmful model outputs**. Generated `responses.jsonl`
  is git-ignored. For the harmful set we record only the *label* (refused / complied),
  not the content, in published artifacts; any complied harmful output is reviewed and
  not redistributed.
- The benign set is the contribution; the harmful set is a control.

## Benign prompts

Built from public, openly-licensed material: CWE/CVE descriptions
(cwe.mitre.org / nvd.nist.gov), defensive and CTF write-ups, StackOverflow-style
developer questions, and synthetic log snippets. Provenance is recorded per item
(`source`). Verify each third-party source's license before redistribution.

## Third-party datasets

XSTest (CC BY 4.0) and OR-Bench are downloaded, not redistributed here, and used
under their stated licenses. Cite the original papers.

## Models

"Uncensored"/abliterated community models are evaluated **only** as the less-aligned
contrast for the alignment-tax analysis (RQ2). Their provenance and licenses are
documented in the thesis; they are not recommended for deployment.

## Intended use

The output is an empirical basis for choosing models, quantization levels, and
prompting strategies for **defensive**, on-premise security/SWE assistance under
data-privacy constraints (GDPR/DSGVO). It is not intended to facilitate misuse.
