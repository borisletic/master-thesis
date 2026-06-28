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
    """Every core-tier pair_id has exactly one benign and one harmful member.

    Hard-tier prompts are intentionally unpaired over-refusal stress tests.
    """
    core = [p for p in load_security_swe() if p.tier == "core"]
    by_pair: dict[str, list] = {}
    for p in core:
        by_pair.setdefault(p.pair_id, []).append(p)
    for pair_id, members in by_pair.items():
        golds = sorted(m.gold for m in members)
        assert golds == [GOLD_COMPLY, GOLD_REFUSE], f"{pair_id}: {golds}"


def test_core_tier_balanced():
    """The paired core tier is balanced by construction (hard tier is benign-only)."""
    core = [p for p in load_security_swe() if p.tier == "core"]
    benign = [p for p in core if p.gold == GOLD_COMPLY]
    harmful = [p for p in core if p.gold == GOLD_REFUSE]
    assert len(benign) == len(harmful), "core tier should be balanced"


def test_hard_tier_is_benign_and_unpaired():
    hard = [p for p in load_security_swe() if p.tier == "hard"]
    assert hard, "expected hard-tier stress prompts"
    for p in hard:
        assert p.gold == GOLD_COMPLY
        assert p.pair_id is None
