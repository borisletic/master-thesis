# 1. Introduction

## 1.1 Motivation

Modern large language models (LLMs) undergo *safety alignment* so that they refuse
to assist with harmful requests — producing malware, planning attacks, generating
abuse. This is desirable. But alignment optimizes a model toward *harmlessness*,
and harmlessness is in tension with *helpfulness*. When the tension is resolved
badly, the model becomes **over-cautious**: it refuses requests that are completely
benign, simply because their surface form — a word, a phrase, a topic — resembles
something harmful. Röttger et al. (2024) named this **exaggerated safety** and gave
the now-canonical example: a model refusing "How can I kill a Python process?"
because of the word *kill*.

For most domains over-refusal is a nuisance. For **security software engineering**
it is a deployment blocker. The legitimate, everyday vocabulary of the field *is*
the vocabulary of attack: a defender analyzing a log full of the word "attack", a
developer asking how to fix a SQL *injection*, an incident responder detonating a
*malware* sample in a sandbox, an engineer asking how to *kill* a runaway process.
If a model refuses these, it is useless for the very work it was deployed to
support.

This matters most precisely where the constraints are tightest. Business-sensitive
source code and incident data often cannot be sent to a cloud API for legal and
privacy reasons (GDPR/DSGVO). The pragmatic response is to run a **small model
locally**, on-premise, on consumer hardware — which requires **quantization** to
fit in limited VRAM. The folklore is that small, heavily-quantized models are the
most fragile: most likely to be miscalibrated, most likely to over-refuse. Whether
that folklore is true is an empirical question this thesis sets out to answer.

## 1.2 Problem statement

We study, by inference alone (no training or fine-tuning), three coupled questions
about small locally-served models in the security-SWE domain:

1. *How severe is over-refusal* on benign security tasks, relative to a calibrated
   general-domain benchmark?
2. *What is the alignment tax* — how much helpfulness is sacrificed for safety, and
   is the trade-off "worth it"?
3. *Does quantization shift this behavior*, and in which direction?

The system under study takes a natural-language request as input and produces a
response that we classify as **compliance** or **refusal**; for benign requests
that are complied with, we additionally score answer **utility**. Every prompt
carries a known gold label — *should-comply* (benign) or *should-refuse* (harmful)
— which makes the evaluation objective.

## 1.3 Research questions

- **RQ1 (domain severity).** How large is the false-refusal rate (FRR) on benign
  security-SWE tasks, compared with the general XSTest benchmark?
- **RQ2 (alignment tax).** How much utility on legitimate security tasks is lost to
  alignment, and does greater benign refusal co-occur with stronger refusal of
  genuinely harmful requests (i.e. is the tax "justified")?
- **RQ3 (quantization × over-refusal).** Does quantization (8-bit → 4-bit) move
  over-refusal of benign tasks, and in which direction? Prior work studies the
  *harmful-compliance* direction; the benign-refusal direction is unexplored.
- **RQ4 (lexical vs. contextual).** Which triggers drive over-refusal — individual
  "dangerous" words, or sensitive topics/contexts? Is the failure lexical or
  contextual?

## 1.4 Contributions

1. A **purpose-built Security-SWE Over-Refusal dataset**: paired benign/harmful
   prompts across ten security task families, plus an adversarial *hard* tier of
   high-pressure, dual-use, and own-system framings that probe the true
   over-refusal boundary.
2. A **systematic six-model evaluation** on commodity hardware (RTX 4060, 8 GB)
   spanning alignment strength and quantization level, answering RQ1–RQ4 with
   **human-validated** refusal labels.
3. The first measurement, to our knowledge, of **quantization's effect on benign
   over-refusal** (RQ3), with temperature repeats for statistical honesty and
   replication across two model families.
4. A **methodological finding**: refusal classification is the dominant source of
   measurement uncertainty; a purely lexical heuristic — the kind often used in
   practice — recovers only 12% of true refusals, swinging headline metrics 2–4×.
5. An **open, reproducible pipeline** (local inference, classification, metrics,
   analysis) and a concrete deployment recommendation.

## 1.5 Thesis structure

Chapter 2 reviews related work. Chapter 3 presents the Security-SWE dataset.
Chapter 4 describes the method (model matrix, classifier, metrics). Chapter 5
reports results for RQ1–RQ4 plus the classifier-validation finding. Chapter 6
discusses implications, limitations, and threats to validity. Chapter 7 concludes.
