"""Generate the thesis/paper figures from the validated results.

Four figures, all with the uncertainty made visible (that is the point — the
point estimates alone overstate what n=18 supports):

  fig1_tradeoff.png   over-refusal vs retained safety, with 95% CIs
  fig2_xstest_types.png  FRR by XSTest prompt type — lexical vs contextual
  fig3_quantization.png  Q4 vs Q8 across temperature, mean +/- sd
  fig4_utility.png    the alignment tax split into quality vs delivered utility

Needs matplotlib (see requirements-figures.txt); the core pipeline does not.

Usage:
    python -m scripts.make_figures
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from orr.datasets import load_security_swe  # noqa: E402
from orr.evaluation.stats import wilson_ci  # noqa: E402

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"
_FIGS = _REPO / "docs" / "figures"

SHORT = {
    "mistral:latest": "mistral-7B",
    "phi3.5:3.8b-mini-instruct-q4_0": "phi-3.5",
    "qwen2.5:7b-instruct-q4_K_M": "qwen Q4",
    "qwen2.5:7b-instruct-q8_0": "qwen Q8",
    "gemma2:9b-instruct-q4_K_M": "gemma2-9B",
    "llama3.1:8b-instruct-q4_K_M": "llama3.1-8B",
}
# three statistically distinguishable groups (see scripts/analyze_stats.py)
GROUP = {
    "mistral-7B": "permissive / unsafe", "phi-3.5": "permissive / unsafe",
    "qwen Q4": "balanced", "qwen Q8": "balanced",
    "gemma2-9B": "max-safety / over-refusing", "llama3.1-8B": "max-safety / over-refusing",
}
COLOR = {"permissive / unsafe": "#d1495b", "balanced": "#2a9d8f",
         "max-safety / over-refusing": "#3d5a80"}

plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.titlesize": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 300, "savefig.bbox": "tight",
})


def load(globs=("2026*sweep*", "*hard2*"), name="responses_hybrid.jsonl"):
    """Sweep + hard2 dirs so the hard tier reflects the full n=100 (dedup last-wins)."""
    if isinstance(globs, str):
        globs = (globs,)
    tier = {p.id: p.tier for p in load_security_swe()}
    seen = {}
    dirs = []
    for g in globs:
        dirs.extend(sorted(_RESULTS.glob(g)))
    for d in dirs:
        f = d / name
        if not f.exists():
            continue
        for line in f.open(encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                r["tier"] = tier.get(r["prompt_id"], "core")
                seen[(r["model"], r["prompt_id"])] = r
    return list(seen.values())


def _counts(rows, model, dataset, gold, tier=None):
    sel = [r for r in rows if r["model"] == model and r["dataset"] == dataset
           and r["gold"] == gold and (tier is None or r["tier"] == tier)]
    return sum(1 for r in sel if r["pred"] == "refusal"), len(sel)


# --------------------------------------------------------------------- fig 1
def fig_tradeoff(rows):
    fig, ax = plt.subplots(figsize=(5.5, 4))
    seen = set()
    for m, short in SHORT.items():
        kf, nf = _counts(rows, m, "security_swe", "should_comply", tier="hard")
        kt, nt = _counts(rows, m, "security_swe", "should_refuse")
        if nf == 0:
            continue
        f, t = wilson_ci(kf, nf), wilson_ci(kt, nt)
        g = GROUP[short]
        ax.errorbar(f.point * 100, t.point * 100,
                    xerr=[[(f.point - f.lo) * 100], [(f.hi - f.point) * 100]],
                    yerr=[[(t.point - t.lo) * 100], [(t.hi - t.point) * 100]],
                    fmt="o", ms=7, capsize=3, lw=1, color=COLOR[g],
                    label=g if g not in seen else None, zorder=3)
        seen.add(g)
        # nudge the two max-safety labels apart; they sit almost on top of each other
        off = {"gemma2-9B": (-6, 10), "llama3.1-8B": (6, -14)}.get(short, (7, -3))
        ha = "right" if off[0] < 0 else "left"
        ax.annotate(short, (f.point * 100, t.point * 100),
                    textcoords="offset points", xytext=off, fontsize=8, ha=ha)
    ax.set_xlabel("Over-refusal — FRR on hard tier (%)")
    ax.set_ylabel("Retained safety — TRR (%)")
    ax.set_title("Over-refusal vs. safety (95% Wilson intervals)")
    ax.set_xlim(-8, 100); ax.set_ylim(0, 110)
    ax.grid(alpha=.25, lw=.5)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.text(0.5, -0.04, "Intervals overlap within groups: only the between-group "
             "contrasts are statistically supported.", ha="center", fontsize=7,
             style="italic")
    out = _FIGS / "fig1_tradeoff.png"
    fig.savefig(out); plt.close(fig)
    return out


# --------------------------------------------------------------------- fig 2
def fig_xstest_types(rows):
    types, per = {}, {}
    for m, short in SHORT.items():
        sel = [r for r in rows if r["model"] == m and r["dataset"] == "xstest"
               and r["gold"] == "should_comply"]
        by = {}
        for r in sel:
            c = r["category"]
            by.setdefault(c, [0, 0])
            by[c][1] += 1
            if r["pred"] == "refusal":
                by[c][0] += 1
        per[short] = {c: v[0] / v[1] * 100 for c, v in by.items() if v[1]}
        types.update({c: 1 for c in by})
    order = sorted(types, key=lambda c: -max(per[s].get(c, 0) for s in per))
    lexical = {"homonyms", "figurative_language", "definitions"}

    fig, ax = plt.subplots(figsize=(6.5, 4))
    x = range(len(order))
    for short in per:
        ax.plot(list(x), [per[short].get(c, 0) for c in order], marker="o", ms=3.5,
                lw=1, alpha=.85, label=short)
    ax.set_xticks(list(x))
    ax.set_xticklabels([c.replace("_", " ") for c in order], rotation=35,
                       ha="right", fontsize=7.5)
    for i, c in enumerate(order):
        if c in lexical:
            ax.get_xticklabels()[i].set_color("#b5651d")
            ax.get_xticklabels()[i].set_fontweight("bold")
    ax.set_ylabel("False refusal rate (%)")
    ax.set_title("XSTest: refusals concentrate on sensitive topics, not trigger words")
    ax.grid(alpha=.25, lw=.5, axis="y")
    ax.legend(frameon=False, fontsize=7.5, ncol=2)
    fig.text(0.5, -0.16, "Bold/orange labels are the lexical types (homonyms, "
             "figurative language, definitions) — uniformly low.",
             ha="center", fontsize=7, style="italic")
    out = _FIGS / "fig2_xstest_types.png"
    fig.savefig(out); plt.close(fig)
    return out


# --------------------------------------------------------------------- fig 3
def fig_quantization():
    import re
    from statistics import mean, pstdev
    tag = re.compile(r"rq3-(?P<model>.+?)-t(?P<temp>[0-9.]+)-r(?P<rep>\d+)$")
    cells = {}
    for d in sorted(_RESULTS.glob("*rq3*")):
        m = tag.search(d.name)
        f = d / "responses_hybrid.jsonl"
        if not m or not f.exists():
            continue
        rs = [json.loads(l) for l in f.open(encoding="utf-8") if l.strip()]
        harm = [r for r in rs if r["gold"] == "should_refuse"]
        if not harm:
            continue
        trr = sum(1 for r in harm if r["pred"] == "refusal") / len(harm) * 100
        fam = "qwen2.5-7B" if "qwen" in m["model"] else "llama3.1-8B"
        quant = "Q8" if "q8" in m["model"].lower() else "Q4"
        cells.setdefault((fam, quant, float(m["temp"])), []).append(trr)

    fams = sorted({k[0] for k in cells})
    fig, axes = plt.subplots(1, len(fams), figsize=(7, 3.2), sharey=True)
    if len(fams) == 1:
        axes = [axes]
    for ax, fam in zip(axes, fams):
        for quant, col in (("Q4", "#e07a5f"), ("Q8", "#3d5a80")):
            temps = sorted({k[2] for k in cells if k[0] == fam and k[1] == quant})
            mus = [mean(cells[(fam, quant, t)]) for t in temps]
            sds = [pstdev(cells[(fam, quant, t)]) if len(cells[(fam, quant, t)]) > 1
                   else 0 for t in temps]
            ax.errorbar(temps, mus, yerr=sds, marker="o", ms=5, capsize=3, lw=1.2,
                        color=col, label=quant)
        ax.set_title(fam, fontsize=9)
        ax.set_xlabel("temperature")
        ax.grid(alpha=.25, lw=.5)
        ax.set_xticks([0.0, 0.7, 1.0])
    axes[0].set_ylabel("True refusal rate (%)")
    axes[0].legend(frameon=False, fontsize=8, title="quantization",
                   title_fontsize=8)
    fig.suptitle("Quantization effect vanishes once sampling variance is shown",
                 fontsize=10, y=1.02)
    out = _FIGS / "fig3_quantization.png"
    fig.savefig(out); plt.close(fig)
    return out


# --------------------------------------------------------------------- fig 4
def fig_utility():
    path = _RESULTS / "utility_scores.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    names, qual, eff = [], [], []
    for full, short in SHORT.items():
        if full in data:
            names.append(short)
            qual.append(data[full]["quality_given_complied"])
            eff.append(data[full]["effective_utility"])
    order = sorted(range(len(names)), key=lambda i: -eff[i])
    names = [names[i] for i in order]
    qual = [qual[i] for i in order]
    eff = [eff[i] for i in order]

    fig, ax = plt.subplots(figsize=(6, 3.4))
    y = range(len(names))
    ax.barh([i + .18 for i in y], qual, height=.34, color="#adb5bd",
            label="quality when it does answer")
    ax.barh([i - .18 for i in y], eff, height=.34, color="#2a9d8f",
            label="effective utility (refusals = 0)")
    for i in y:
        gap = qual[i] - eff[i]
        if gap > 0.02:
            ax.annotate(f"−{gap:.2f}", (qual[i] + .01, i + .18), fontsize=7,
                        va="center", color="#d1495b")
    ax.set_yticks(list(y)); ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("score (0–1)"); ax.set_xlim(0, 1.12)
    ax.set_title("The alignment tax is paid in refusal, not answer quality", pad=26)
    # legend above the axes: inside it collides with the widest bars
    ax.legend(frameon=False, fontsize=8, loc="lower center",
              bbox_to_anchor=(0.5, 1.04), ncol=2)
    ax.grid(alpha=.25, lw=.5, axis="x")
    fig.text(0.5, -0.06, "The gap is the helpfulness destroyed by refusing, "
             "not by answering badly.", ha="center", fontsize=7, style="italic")
    out = _FIGS / "fig4_utility.png"
    fig.savefig(out); plt.close(fig)
    return out


def main(argv=None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    _FIGS.mkdir(parents=True, exist_ok=True)
    rows = load()
    if not rows:
        print("[error] no results found")
        return 1
    for fn in (lambda: fig_tradeoff(rows), lambda: fig_xstest_types(rows),
               fig_quantization, fig_utility):
        out = fn()
        print(f"[ok] {out}" if out else "[skip] missing input")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
