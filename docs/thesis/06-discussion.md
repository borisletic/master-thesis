# 6. Discussion

## 6.1 What the results mean for deployment

The motivating scenario is an organization that must run a model on-premise for
privacy reasons and wants it to help with security software-engineering work without
spuriously refusing. The results give a concrete answer.

- **qwen2.5-7B-Instruct is the best-balanced choice.** It pairs low over-refusal
  (5.6% on the hard tier, ~0% on clearly-benign tasks) with strong safety (TRR
  79% at Q4, 92% at Q8) and high delivered helpfulness (effective utility 0.90–0.93).
  It dominates the alternatives on the joint objective.
- **gemma2-9B and llama3.1-8B are "maximum-safety, low-utility".** Both refuse 100%
  of harmful prompts but forfeit a third of their benign utility (effective utility
  0.71 and 0.63). For a security-triage assistant that must not be obstructive, this
  is the wrong trade — their excellent answer quality is wasted behind refusals.
- **mistral-7B and phi-3.5 are "permissive, unsafe".** They rarely over-refuse but
  comply with most harmful requests (TRR 41.7% and 20.8%). Unsuitable where the
  model might be asked to produce genuinely harmful artifacts.
- **Quantization can be chosen for cost, not behavior.** Since Q4↔Q8 has no robust
  behavioral effect (RQ3), one may pick the smaller, faster 4-bit weights without a
  meaningful over-refusal or safety penalty — relevant because 8-bit 8B models
  overflow 8 GB and run ~3× slower via CPU offload.

## 6.2 Why over-refusal is contextual, and why that is good news for security

RQ4's finding — that over-refusal tracks sensitive *topics*, not *words* — is
encouraging for the security domain specifically. The field's hazard was always
assumed to be lexical: that "exploit", "payload", "attack" would trip a keyword
reflex. But these models have largely outgrown lexical over-refusal (homonyms
0–16%). What remains is topical sensitivity (privacy, discrimination) that mostly
does *not* overlap with defensive security work. The residual security over-refusals
are not keyword reflexes but genuine *intent* ambiguity — "act as the attacker",
"bypass my own login" — where even a human reviewer might hesitate. This reframes
the mitigation target: not keyword desensitization, but better contextual/intent
disambiguation.

## 6.3 The measurement lesson

Perhaps the most transferable result is methodological: the choice of refusal
classifier moved every headline number by 2–4×, and a lexical heuristic — a common
shortcut in over-refusal tooling — recovered only 12% of true refusals. Soft
refusals and "I can't do X, but here's safe Y" redirects are invisible to pattern
matching but obvious to a judge model and to humans. **Over-refusal numbers are only
as trustworthy as the classifier behind them**, and that classifier must be validated
against human labels. We suspect some cross-paper disagreement in the literature is
attributable to unvalidated, lexically-biased refusal detection.

## 6.4 Limitations

- **Dataset size.** 66 own-prompts (24 harmful, 42 benign) is enough to expose the
  effects but small for fine-grained per-category claims; the hard tier (18) makes
  individual hard-tier percentages coarse (each prompt ≈ 5.6 pp).
- **Single annotator.** Validation used one human annotator; full inter-annotator
  agreement (a second labeler, especially on the `contested` hard prompts) is future
  work.
- **Self-grading bias.** Both the refusal judge and the utility grader are qwen2.5-7B,
  which also appears as a model under test — a possible mild self-preference. The
  headline conclusions are robust to this (they are driven by *validated refusal
  counts*, not grades), but absolute quality values would benefit from a second,
  independent grader.
- **Six models, two families for RQ3.** Findings may not extend to every
  architecture or to more extreme quantization (e.g. 2-bit / 3-bit), which we did
  not test.
- **No system-prompt arm.** Röttger et al. show system prompts can flip behavior; we
  used none, so results reflect default behavior, not best-case prompting.
- **Greedy primary runs.** Only RQ3 used temperature repeats; the cross-model table
  is single-run (though deterministic).

## 6.5 Threats to validity

- *Construct validity*: the should-comply/should-refuse boundary is a judgment;
  `contested` flags mark where it is genuinely debatable, and these are exactly the
  prompts that produced the residual refusals — so RQ-level conclusions do not hinge
  on contested edge labels.
- *Internal validity*: deterministic seeds and a fixed pipeline control run-to-run
  variation; RQ3 explicitly quantifies sampling variance.
- *External validity*: results are for small (≤9B) GGUF models on 8 GB hardware in
  English; they should not be extrapolated to large/cloud models or other languages
  without re-testing.
