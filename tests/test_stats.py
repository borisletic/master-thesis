"""Tests for the statistical helpers (Wilson CI, Fisher exact, Holm correction)."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orr.evaluation.stats import (  # noqa: E402
    wilson_ci, fisher_exact, compare, holm_bonferroni,
)


def test_wilson_contains_point_estimate():
    ci = wilson_ci(13, 18)
    assert ci.lo < ci.point < ci.hi
    assert abs(ci.point - 13 / 18) < 1e-12


def test_wilson_bounded_and_never_degenerate_at_extremes():
    """Normal approximation gives a zero-width interval at k=0; Wilson must not."""
    lo0 = wilson_ci(0, 18)
    assert lo0.lo == 0.0 and lo0.hi > 0.0
    hi1 = wilson_ci(18, 18)
    assert hi1.hi == 1.0 and hi1.lo < 1.0


def test_wilson_narrows_with_n():
    assert wilson_ci(5, 10).width_pp > wilson_ci(50, 100).width_pp


def test_fisher_known_values():
    # identical proportions -> nothing to detect
    assert fisher_exact(5, 5, 5, 5) == 1.0
    # complete separation on a decent sample -> strongly significant
    assert fisher_exact(10, 0, 0, 10) < 0.001
    # p-values stay in range
    assert 0.0 <= fisher_exact(13, 5, 10, 8) <= 1.0


def test_fisher_symmetric_in_row_order():
    assert abs(fisher_exact(10, 8, 1, 17) - fisher_exact(1, 17, 10, 8)) < 1e-12


def test_thesis_headline_comparisons():
    """Regression guard on the numbers quoted in the thesis."""
    # gemma vs qwen-Q4 on the hard tier: significant
    assert fisher_exact(10, 8, 1, 17) < 0.05
    # llama vs gemma on the hard tier: NOT significant (n is too small)
    assert fisher_exact(13, 5, 10, 8) > 0.05
    # qwen Q8 vs Q4 true-refusal: NOT significant -> supports the RQ3 null
    assert fisher_exact(22, 2, 19, 5) > 0.05


def test_compare_reports_both_sides():
    r = compare(13, 18, 1, 18)
    assert r["a"]["k"] == 13 and r["b"]["k"] == 1
    assert r["diff_pp"] > 0
    assert 0.0 <= r["p_value"] <= 1.0


def test_holm_is_monotone_and_conservative():
    out = holm_bonferroni({"x": 0.001, "y": 0.20, "z": 0.49})
    assert out["x"]["p_adj"] >= out["x"]["p_raw"]
    assert out["x"]["p_adj"] <= out["y"]["p_adj"] <= out["z"]["p_adj"]
    assert out["x"]["significant"] and not out["z"]["significant"]
