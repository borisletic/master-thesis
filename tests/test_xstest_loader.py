"""Guarded tests for the XSTest loader — skipped if the dataset isn't downloaded.

XSTest is fetched (not committed) via scripts/download_datasets.py. These tests
guard against the substring bug where "unsafe".contains("safe") mislabeled all
prompts as safe.
"""
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orr.datasets import load_xstest  # noqa: E402
from orr.datasets.loaders import GOLD_COMPLY, GOLD_REFUSE  # noqa: E402

_HAS_XSTEST = bool(load_xstest())


@pytest.mark.skipif(not _HAS_XSTEST, reason="XSTest not downloaded")
def test_xstest_split():
    prompts = load_xstest()
    comply = sum(1 for p in prompts if p.gold == GOLD_COMPLY)
    refuse = sum(1 for p in prompts if p.gold == GOLD_REFUSE)
    # canonical XSTest v2: 250 safe + 200 unsafe contrasts
    assert comply == 250, comply
    assert refuse == 200, refuse


@pytest.mark.skipif(not _HAS_XSTEST, reason="XSTest not downloaded")
def test_xstest_unsafe_not_mislabeled():
    """Regression: 'unsafe' must not be read as safe via substring match."""
    prompts = load_xstest()
    assert any(p.gold == GOLD_REFUSE for p in prompts)
