# Thesis outline

Working title: **Evaluating Over-Refusal and the Alignment–Utility Trade-off in
Small Local Language Models** (security software-engineering domain).

1. **Introduction**
   - Over-refusal / exaggerated safety; why it matters for security-SWE.
   - On-premise/quantized deployment motivation (GDPR/DSGVO).
   - Contributions: (a) domain over-refusal benchmark, (b) alignment-tax study,
     (c) **quantization × benign over-refusal** (novel direction).

2. **Background & related work**
   - XSTest (Röttger et al. 2024) — exaggerated safety, lexical over-fitting.
   - OR-Bench (Cui et al. 2024) — scale.
   - Quantization × safety (Wee et al. 2026; "Quantization Undoes Alignment") —
     harmful-compliance direction → the gap this thesis fills.
   - Scenario-based diagnostics (arXiv:2510.08158).

3. **The Security-SWE Over-Refusal dataset**
   - Design (paired benign/harmful), categories, trigger words, sourcing.
   - Annotation protocol, inter-annotator agreement.

4. **Method**
   - Model matrix (alignment × quantization); local inference stack.
   - Refusal classifier (heuristic + LLM judge); human validation, κ.
   - Metrics (FRR, safe-compliance, TRR, alignment tax).

5. **Results**
   - RQ1 domain vs general severity.
   - RQ2 alignment tax + justification (FRR↔TRR).
   - RQ3 quantization sweep.
   - RQ4 lexical vs contextual (trigger words, paired-contrast gap).

6. **Discussion** — deployment guidance; limitations; threats to validity.

7. **Conclusion & future work.**

Appendices: full prompt list, classifier patterns, per-model tables, ethics.

## References

- P. Röttger et al. *XSTest.* NAACL 2024. arXiv:2308.01263.
- J. Cui et al. *OR-Bench.* 2024.
- S. Wee et al. *Alignment-Aware Quantization for LLM Safety.* arXiv:2511.07842, 2026.
- *Beyond Over-Refusal.* arXiv:2510.08158, 2025.
- *Quantization Undoes Alignment.* arXiv:2605.15208, 2026.
