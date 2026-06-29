# 7. Conclusion and Future Work

## 7.1 Summary

This thesis measured over-refusal and the alignment–utility trade-off in six small,
locally-served language models on commodity hardware, in the security
software-engineering domain. Using a purpose-built paired/tiered Security-SWE
dataset alongside XSTest, and a human-validated hybrid refusal classifier, we
answered four research questions:

- **RQ1.** Security-domain over-refusal is model-dependent, not universal; for
  safety-aggressive models (gemma2, llama3.1) it exceeds general-domain
  over-refusal, while well-balanced models (qwen) handle security vocabulary
  comfortably. The phenomenon is concentrated in adversarially-framed *hard* prompts;
  clearly-benign security prompts are essentially never refused.
- **RQ2.** Over-refusal and safety form a monotonic trade-off, and the alignment tax
  is paid almost entirely through **refusal, not answer quality**. The
  highest-quality model (llama3.1, 0.98) delivers the lowest effective utility (0.63)
  because it refuses a third of benign tasks. High safety and high utility are
  jointly achievable (qwen), so the steep tax some models pay is avoidable.
- **RQ3.** Quantization from 8-bit to 4-bit has **no robust effect** on benign
  over-refusal or on safety once temperature variance is accounted for, replicated
  across two model families. An apparent greedy-decoding effect vanishes under
  sampling — a caution against single-run quantization studies.
- **RQ4.** Over-refusal is **contextual, not lexical**: sensitive topics drive
  refusals (privacy_fictional 56–76%) while classic word-level triggers (homonyms,
  figurative language) barely register (0–16%).

A fifth, methodological result threads through all of these: **refusal classification
is the dominant measurement uncertainty.** A lexical heuristic recovered only 12% of
true refusals and swung headline metrics 2–4×; only the human-validated judge
(κ = 0.72) gives trustworthy numbers.

## 7.2 Practical recommendation

For on-premise security-SWE assistance under privacy constraints on an 8 GB GPU,
**qwen2.5-7B-Instruct** is the recommended model: it minimizes over-refusal while
retaining strong safety and high delivered utility, and — because quantization is
behaviorally neutral here — its fast, memory-light **4-bit** weights can be used
without penalty.

## 7.3 Future work

1. **Scale and breadth.** Grow the Security-SWE dataset toward 100+ pairs with a
   second annotator and reported inter-annotator agreement; add more architectures
   and more extreme quantization (3-bit, 2-bit) to test the generality of RQ3.
2. **Independent grading.** Re-score utility and refusals with a second,
   non-participating judge (or a stronger cloud "ceiling" model) to remove the
   self-preference risk and obtain firmer absolute quality values.
3. **Mitigation.** Having localized over-refusal to contextual/intent ambiguity
   (RQ4), test targeted mitigations — system prompts, intent-clarification prompting,
   light contextual fine-tuning — and measure their effect on the hard tier without
   regressing safety.
4. **OR-Bench at scale.** Add the large OR-Bench benign set to complement XSTest and
   confirm the lexical-vs-contextual finding at scale.
5. **Utility rubric per task.** Replace the coarse 0–2 grade with task-specific
   correctness checks (e.g. does the CWE fix actually parameterize the query) for a
   sharper utility axis.

## 7.4 Artifacts

The dataset, inference/classification/metrics pipeline, validation tooling, all run
manifests, and aggregated metrics are provided in the project repository, enabling
full reproduction on a single consumer GPU.
