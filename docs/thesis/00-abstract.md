# Abstract

Safety alignment teaches large language models (LLMs) to refuse harmful requests,
but a well-documented side effect is **over-refusal** ("exaggerated safety"): the
model also declines benign requests that merely *resemble* harmful ones in wording.
This is acute in **security software engineering**, where legitimate work is
saturated with dangerous-sounding vocabulary — *attack*, *exploit*, *payload*,
*inject*, *kill*, *reverse shell*, *malware*. Organizations that, for privacy
reasons (GDPR/DSGVO), deploy small quantized models **on-premise** are exactly the
ones exposed to this failure: the smaller the model and the more aggressive the
quantization, the more fragile its calibration is assumed to be.

This thesis presents a systematic, inference-only evaluation of over-refusal and
the alignment–utility trade-off in six small, locally-served models
(mistral-7B, qwen2.5-7B-Instruct in 4- and 8-bit, llama3.1-8B-Instruct,
gemma2-9B-Instruct, phi-3.5-mini) on a single consumer GPU (RTX 4060, 8 GB). We
introduce a purpose-built **Security-SWE Over-Refusal** dataset of paired benign /
harmful prompts plus an adversarial "hard" tier, and evaluate alongside the general
XSTest benchmark. Refusals are detected by a hybrid heuristic + LLM-judge
classifier that we **validate against human labels** (Cohen's κ = 0.72).

We find four results. **(RQ1)** Over-refusal in the security domain is not
universal but model-dependent; when present it can exceed general-domain
over-refusal. **(RQ2)** Over-refusal and safety form a clean monotonic trade-off,
and — crucially — the alignment tax is paid almost entirely through *refusal*, not
through degraded answer *quality*: the model with the highest answer quality
(llama3.1, 0.98) delivers the **lowest** effective utility (0.63) because it
refuses a third of benign security tasks. **(RQ3)** Quantization from 8-bit to
4-bit has *no robust effect* on either over-refusal or safety once temperature
variance is accounted for — an apparent effect under greedy decoding disappears
under sampling, in both model families tested. **(RQ4)** Over-refusal is driven by
sensitive *topics*, not by trigger *words*: lexical-homonym prompts ("kill a
process") are refused 0–16% of the time, while sensitive-topic prompts reach
56–76%. A fifth, methodological finding emerges throughout: refusal classification
is the dominant source of measurement uncertainty — a fast lexical heuristic
recovers only 12% of true refusals — so any over-refusal number reported without a
validated classifier is unreliable.

The study yields a concrete deployment recommendation (qwen2.5-7B-Instruct as the
best-balanced on-premise choice) and an open, reproducible pipeline.
