"""Integrity checks on the own Security-SWE dataset."""
from orr.datasets import load_security_swe
from orr.datasets.loaders import GOLD_COMPLY, GOLD_REFUSE


def test_dataset_loads():
    prompts = load_security_swe()
    assert len(prompts) >= 40


def test_ids_unique():
    prompts = load_security_swe()
    ids = [p.id for p in prompts]
    assert len(ids) == len(set(ids)), "duplicate ids"


def test_labels_valid():
    for p in load_security_swe():
        assert p.gold in (GOLD_COMPLY, GOLD_REFUSE)
        assert p.text.strip()
        assert p.trigger_words, f"{p.id} has no trigger words"


def test_pairs_are_complete():
    """Every pair_id should have exactly one benign and one harmful member."""
    prompts = load_security_swe()
    by_pair: dict[str, list] = {}
    for p in prompts:
        by_pair.setdefault(p.pair_id, []).append(p)
    for pair_id, members in by_pair.items():
        golds = sorted(m.gold for m in members)
        assert golds == [GOLD_COMPLY, GOLD_REFUSE], f"{pair_id}: {golds}"


def test_balanced():
    prompts = load_security_swe()
    benign = [p for p in prompts if p.gold == GOLD_COMPLY]
    harmful = [p for p in prompts if p.gold == GOLD_REFUSE]
    assert len(benign) == len(harmful), "dataset should be balanced by construction"
