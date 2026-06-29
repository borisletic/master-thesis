# 2. Background and Related Work

## 2.1 Over-refusal / exaggerated safety

**Röttger et al. (2024), XSTest.** The foundational work on over-refusal introduces
XSTest, a hand-built test suite of 250 *safe* prompts that a well-calibrated model
should answer, each constructed around a "dangerous-sounding" cue, plus 200
genuinely *unsafe* contrast prompts. The safe prompts span ten types — homonyms
(*kill a process*), figurative language, safe targets, safe contexts, definitions,
real/nonsense discrimination, historical events, and public/fictional privacy. The
central finding is that over-refusal stems from **lexical overfitting**:
models become hypersensitive to individual tokens. GPT-4 achieves the best balance;
system prompts can flip behavior substantially. XSTest is the calibrated
general-domain baseline we adopt (CC BY 4.0).

**Cui et al. (2024), OR-Bench.** The first *large-scale* over-refusal benchmark.
Rather than hand-writing prompts, OR-Bench automatically generates tens of
thousands of "seemingly toxic" benign prompts likely to be wrongly refused,
revealing patterns that small manual suites miss. It establishes that even strong
models refuse a non-trivial fraction of benign requests at scale.

**Scenario-based diagnostics (arXiv:2510.08158).** Recent work extends XSTest with
benchmarks (XSB / MS-XSB) that separate *lexical* over-sensitivity from failures of
*contextual integration*, and adds post-hoc mitigation. It signals that the field's
measurement methodology is maturing and that the lexical-vs-contextual distinction
(our RQ4) is an active question.

**Where this thesis differs.** All of the above are general-domain, English, and
evaluated primarily on large/cloud models. None isolate the **security software
engineering** domain, none study **small locally-served** models, and none examine
**quantization**. The canonical "kill a process" example is itself a programming
question — a hint that software engineering is disproportionately exposed.

## 2.2 Quantization and safety

Quantization compresses model weights (e.g. to 8-bit or 4-bit) so models fit on
consumer GPUs. The question is whether it is *behaviorally* neutral.

**Wee et al. (2026), Alignment-Aware Quantization (arXiv:2511.07842)** and the
related **"Quantization Undoes Alignment" (arXiv:2605.15208)** show it is not.
Post-training quantization can partially undo safety fine-tuning, making models
*more* willing to comply with harmful requests — a dose-dependent degradation that
is invisible to standard metrics (perplexity stays low). Both works measure the
**harmful-compliance** direction: does quantization make the model *less safe*?

**The gap this thesis fills.** The opposite direction — whether quantization changes
**benign over-refusal** — is unstudied, and especially so in a concrete domain. RQ3
addresses exactly this: does compressing a model make it refuse *more* (or fewer)
benign tasks? We also import a methodological lesson from this literature: because
quantization effects are small and can be masked by aggregate metrics, single
deterministic runs are insufficient — we use temperature repeats and report
mean ± standard deviation.

## 2.3 The alignment–utility trade-off

The tension between harmlessness and helpfulness is intrinsic to alignment. The
"alignment tax" is usually discussed qualitatively. This thesis operationalizes it
in the security domain along two axes simultaneously: (i) the *refusal* axis —
false-refusal rate on benign tasks vs. true-refusal rate on harmful tasks — and
(ii) the *quality* axis — graded helpfulness of the answers that are given. Treating
these separately turns out to matter (Chapter 5, RQ2): the tax manifests through
refusal, not through answer quality.

## 2.4 Positioning

| Aspect                     | XSTest | OR-Bench | Wee et al. / "Undoes Alignment" | **This thesis** |
|----------------------------|:------:|:--------:|:-------------------------------:|:---------------:|
| Over-refusal (benign)      |   ✔    |    ✔     |                                 |       ✔         |
| Security-SWE domain        |        |          |                                 |       ✔         |
| Small *local* models       |        |          |               ~                 |       ✔         |
| Quantization               |        |          |   ✔ (harmful-compliance)        | ✔ (**benign refusal**) |
| Alignment tax incl. utility|        |          |                                 |       ✔         |
| Human-validated classifier |   ✔    |    ~     |               ~                 |       ✔         |

This work sits at the intersection that prior art leaves empty: benign over-refusal,
in the security-SWE domain, on small quantized on-premise models, with the
quantization direction inverted relative to existing safety-under-compression work.
