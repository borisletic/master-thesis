# Thesis

**Evaluating Over-Refusal and the Alignment–Utility Trade-off in Resource-Constrained
Local Language Models** — domain: security software engineering.

All quantitative claims use the human-validated hybrid classifier (Cohen's
κ = 0.72), the expanded hard tier (_n_ = 100), and proper uncertainty (Wilson
intervals, Fisher exact + Holm correction). See [docs/FINDINGS.md](../FINDINGS.md)
for the running log and `results/` for raw data.

## Deliverables

| Document | Language | Location |
|----------|----------|----------|
| **Master thesis** (50 pp, 22 tables, 5 figures) | Serbian (Cyrillic) | `Master_rad_BorisLetic.docx` |
| **Conference paper** (4 pp) | Serbian | [`../paper/Zbornik_BorisLetic.docx`](../paper/Zbornik_BorisLetic.docx) |
| **arXiv preprint** | English | [`../arxiv/main.tex`](../arxiv/main.tex) |

## Rebuilding the thesis

The `.docx` is generated (not hand-edited) from Python so numbers stay in sync:

```bash
cd docs/thesis
python build_docx.py --template <FTN_template.docx> --out Master_rad_BorisLetic.docx
```

A previously built `.docx` also works as the template (its styles are the FTN ones);
unreferenced template images are dropped automatically so figures are not duplicated.
**After every rebuild, open the file in Word and press Ctrl+A then F9** — the table of
contents is a field and its page numbers are only filled in on that update.

Content lives in `content.py` (ch. 1–2) and `ch2.py`, `ch3_4.py`, `ch5_6.py`,
`ch7_9.py`. `build_docx.py` copies the FTN template's styles and swaps the body;
tables/figures are auto-numbered with symbolic `{{T:key}}` / `{{F:key}}`
references resolved at build time.

> The earlier chapter-by-chapter English Markdown draft was superseded by the
> Serbian `.docx` and the English arXiv preprint, and removed to avoid stale,
> contradictory numbers in the repository.
