"""Statistical treatment of proportion-based metrics.

The core metrics (FRR, TRR) are proportions over small samples — the hard tier
has 18 benign prompts, the harmful control 24 — so point estimates alone are
misleading. This module supplies the interval and hypothesis machinery needed to
state what the data actually supports.

Pure standard library, so it stays part of the core (no numpy/scipy).

  - `wilson_ci`  : 95% confidence interval for a single proportion. Wilson rather
                   than normal-approximation because it behaves correctly near
                   0 and 1 and at small n, which is exactly our regime.
  - `fisher_exact`: two-sided exact test for a 2x2 table. Exact rather than
                   chi-square because expected cell counts are frequently < 5.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Proportion:
    """A proportion with its confidence interval."""
    k: int                 # successes (e.g. refusals)
    n: int                 # trials (e.g. benign prompts)
    point: float           # k / n
    lo: float              # CI lower bound
    hi: float              # CI upper bound

    @property
    def width_pp(self) -> float:
        """CI width in percentage points."""
        return (self.hi - self.lo) * 100

    def fmt(self, pct=True) -> str:
        m = 100 if pct else 1
        s = "%" if pct else ""
        return f"{self.point*m:.1f}{s} [{self.lo*m:.1f}–{self.hi*m:.1f}]"

    def as_dict(self) -> dict:
        return {"k": self.k, "n": self.n, "point": self.point,
                "ci_lo": self.lo, "ci_hi": self.hi, "ci_width_pp": self.width_pp}


def wilson_ci(k: int, n: int, z: float = 1.96) -> Proportion:
    """Wilson score interval for a binomial proportion (default 95%)."""
    if n <= 0:
        return Proportion(k, n, float("nan"), float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return Proportion(k, n, p, max(0.0, centre - half), min(1.0, centre + half))


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test p-value for the table [[a, b], [c, d]].

    Sums the hypergeometric probabilities of all tables no more likely than the
    observed one, conditioning on the margins.
    """
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1, row2, col1 = a + b, c + d, a + c

    def prob(x: int) -> float:
        return (math.comb(row1, x) * math.comb(row2, col1 - x)) / math.comb(n, col1)

    p_obs = prob(a)
    lo = max(0, col1 - row2)
    hi = min(row1, col1)
    # 1e-12 guards against float ties being excluded
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs + 1e-12))


def compare(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Compare two proportions: both CIs, the difference, and an exact p-value."""
    p1, p2 = wilson_ci(k1, n1), wilson_ci(k2, n2)
    return {
        "a": p1.as_dict(),
        "b": p2.as_dict(),
        "diff_pp": (p1.point - p2.point) * 100,
        "p_value": fisher_exact(k1, n1 - k1, k2, n2 - k2),
    }


def significant(p_value: float, alpha: float = 0.05) -> bool:
    return p_value < alpha


def holm_bonferroni(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm-Bonferroni correction for a family of comparisons.

    Reporting many pairwise tests inflates the false-positive rate; Holm controls
    the family-wise error rate while being uniformly more powerful than plain
    Bonferroni.
    """
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    out: dict[str, dict] = {}
    prev_adj = 0.0
    for i, (name, p) in enumerate(ordered):
        adj = min(1.0, max(prev_adj, (m - i) * p))   # enforce monotonicity
        prev_adj = adj
        out[name] = {"p_raw": p, "p_adj": adj, "significant": adj < alpha}
    return out
