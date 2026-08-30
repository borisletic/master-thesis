"""RQ3 precision ladder: Q8 -> Q4 -> Q3 -> Q2, per model family.

Level 1 tested only Q4 vs Q8 and found no robust effect — but that is the range
where prior work (ref [5]) expects none; it reports bias emergence at 3-bit. This
extends the ladder down to Q3_K_M and Q2_K on the same 66-prompt set, with the
temperature repeats, so the question "does aggressive quantization degrade safety
or shift over-refusal?" is answered where the effect is actually expected.

Prints, per family, TRR and FRR (mean +/- sd across temperature repeats) at each
precision, plus a Fisher exact test of the most-compressed vs least-compressed
level pooled across repeats. Writes results/ladder.json and, with --figure, a plot.

Usage:
    python -m scripts.analyze_ladder
    python -m scripts.analyze_ladder --figure
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

from orr.evaluation.stats import fisher_exact

_REPO = Path(__file__).resolve().parents[1]
_RESULTS = _REPO / "results"

_TAG = re.compile(r"rq3-(?P<model>.+?)-t(?P<temp>[0-9.]+)-r(?P<rep>\d+)$")
# precision order, most to least bits
QUANT_ORDER = ["q8_0", "q4_K_M", "q3_K_M", "q2_K"]
QUANT_LABEL = {"q8_0": "Q8", "q4_K_M": "Q4", "q3_K_M": "Q3", "q2_K": "Q2"}


def family_of(model: str) -> str:
    return "qwen2.5-7B" if "qwen" in model else "llama3.1-8B"


def quant_of(model: str) -> str | None:
    for q in QUANT_ORDER:
        if q.lower() in model.lower():
            return q
    return None


def collect(name="responses_hybrid.jsonl"):
    """-> {(family, quant, temp): {'trr':[..], 'frr':[..], 'harm':(k,n), 'ben':(k,n)}}"""
    per = defaultdict(lambda: {"trr": [], "frr": [], "harm_k": 0, "harm_n": 0,
                               "ben_k": 0, "ben_n": 0})
    for d in sorted(_RESULTS.glob("*rq3*")):
        m = _TAG.search(d.name)
        f = d / name
        if not m or not f.exists():
            continue
        q = quant_of(m["model"])
        if q is None:
            continue
        rows = [json.loads(l) for l in f.open(encoding="utf-8") if l.strip()]
        harm = [r for r in rows if r["gold"] == "should_refuse"]
        ben = [r for r in rows if r["gold"] == "should_comply"]
        if not harm:
            continue
        key = (family_of(m["model"]), q, float(m["temp"]))
        trr = sum(1 for r in harm if r["pred"] == "refusal") / len(harm) * 100
        frr = (sum(1 for r in ben if r["pred"] == "refusal") / len(ben) * 100) if ben else 0.0
        per[key]["trr"].append(trr)
        per[key]["frr"].append(frr)
        per[key]["harm_k"] += sum(1 for r in harm if r["pred"] == "refusal")
        per[key]["harm_n"] += len(harm)
        per[key]["ben_k"] += sum(1 for r in ben if r["pred"] == "refusal")
        per[key]["ben_n"] += len(ben)
    return per


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--responses-name", default="responses_hybrid.jsonl")
    ap.add_argument("--figure", action="store_true")
    ap.add_argument("--out", default=str(_RESULTS / "ladder.json"))
    args = ap.parse_args(argv)

    per = collect(args.responses_name)
    if not per:
        print("[error] no rq3 data found")
        return 1
    families = sorted({k[0] for k in per})
    report = {}

    for fam in families:
        quants = [q for q in QUANT_ORDER if any(k[0] == fam and k[1] == q for k in per)]
        temps = sorted({k[2] for k in per if k[0] == fam})
        print(f"\n=== {fam}: precision ladder (TRR %, mean over temps) ===\n")
        print(f"{'precision':<10} " + " ".join(f"t={t:<5}" for t in temps) + "   pooled TRR/FRR")
        print("-" * 70)
        for q in quants:
            cells = []
            for t in temps:
                v = per.get((fam, q, t))
                if v and v["trr"]:
                    cells.append(f"{mean(v['trr']):4.0f}±{pstdev(v['trr']) if len(v['trr'])>1 else 0:<2.0f}")
                else:
                    cells.append("  -  ")
            # pooled across all temps/reps
            hk = sum(per[(fam, q, t)]["harm_k"] for t in temps if (fam, q, t) in per)
            hn = sum(per[(fam, q, t)]["harm_n"] for t in temps if (fam, q, t) in per)
            bk = sum(per[(fam, q, t)]["ben_k"] for t in temps if (fam, q, t) in per)
            bn = sum(per[(fam, q, t)]["ben_n"] for t in temps if (fam, q, t) in per)
            print(f"{QUANT_LABEL[q]:<10} " + " ".join(f"{c:>7}" for c in cells)
                  + f"   TRR {hk}/{hn}={hk/hn*100:.0f}%  FRR {bk}/{bn}={bk/bn*100:.0f}%")
            report.setdefault(fam, {})[QUANT_LABEL[q]] = {
                "trr_pooled": hk / hn, "trr_k": hk, "trr_n": hn,
                "frr_pooled": bk / bn if bn else None, "frr_k": bk, "frr_n": bn}

        # top vs bottom of the ladder, pooled
        if len(quants) >= 2:
            top, bot = quants[0], quants[-1]
            th = report[fam][QUANT_LABEL[top]]
            bh = report[fam][QUANT_LABEL[bot]]
            p_trr = fisher_exact(th["trr_k"], th["trr_n"] - th["trr_k"],
                                 bh["trr_k"], bh["trr_n"] - bh["trr_k"])
            print(f"\n  {QUANT_LABEL[top]} vs {QUANT_LABEL[bot]} TRR (pooled): "
                  f"{th['trr_pooled']*100:.0f}% vs {bh['trr_pooled']*100:.0f}%  "
                  f"Fisher p = {p_trr:.3f}  "
                  f"({'significant' if p_trr < 0.05 else 'n.s.'})")
            report[fam]["_top_vs_bottom_trr_p"] = p_trr

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[written] {args.out}")

    if args.figure:
        _figure(per, families, args)
    return 0


def _figure(per, families, args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 300, "savefig.bbox": "tight"})
    figdir = _REPO / "docs" / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(families), figsize=(7, 3.2), sharey=True)
    if len(families) == 1:
        axes = [axes]
    xpos = {q: i for i, q in enumerate(QUANT_ORDER)}
    for ax, fam in zip(axes, families):
        quants = [q for q in QUANT_ORDER if any(k[0] == fam and k[1] == q for k in per)]
        xs, mus, sds = [], [], []
        for q in quants:
            vals = [v for k, v in per.items() if k[0] == fam and k[1] == q for v in v["trr"]]
            if vals:
                xs.append(xpos[q]); mus.append(mean(vals))
                sds.append(pstdev(vals) if len(vals) > 1 else 0)
        ax.errorbar(xs, mus, yerr=sds, marker="o", ms=6, capsize=3, lw=1.4,
                    color="#3d5a80")
        ax.set_xticks(list(xpos.values()))
        ax.set_xticklabels([QUANT_LABEL[q] for q in QUANT_ORDER])
        ax.set_title(fam, fontsize=9)
        ax.set_xlabel("precision (more bits -> fewer)")
        ax.grid(alpha=.25, lw=.5)
        ax.invert_xaxis()
    axes[0].set_ylabel("True refusal rate (%)")
    fig.suptitle("RQ3 precision ladder: safety across Q8 -> Q2", fontsize=10, y=1.02)
    out = figdir / "fig5_ladder.png"
    fig.savefig(out); plt.close(fig)
    print(f"[figure] {out}")


if __name__ == "__main__":
    raise SystemExit(main())
