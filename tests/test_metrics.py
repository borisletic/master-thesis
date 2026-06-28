from orr.evaluation import summarize
from orr.evaluation.metrics import breakdown_by, mean_std


def test_frr_and_trr():
    records = [
        # 4 benign: 1 refused -> FRR 0.25
        {"gold": "should_comply", "pred": "compliance"},
        {"gold": "should_comply", "pred": "compliance"},
        {"gold": "should_comply", "pred": "partial"},
        {"gold": "should_comply", "pred": "refusal"},
        # 2 harmful: 2 refused -> TRR 1.0
        {"gold": "should_refuse", "pred": "refusal"},
        {"gold": "should_refuse", "pred": "refusal"},
    ]
    s = summarize(records)
    assert s.n_benign == 4
    assert s.n_harmful == 2
    assert abs(s.false_refusal_rate - 0.25) < 1e-9
    assert abs(s.safe_compliance_rate - 0.75) < 1e-9
    assert s.true_refusal_rate == 1.0
    assert s.harmful_compliance_rate == 0.0


def test_empty_groups_give_none():
    s = summarize([{"gold": "should_comply", "pred": "compliance"}])
    assert s.true_refusal_rate is None  # no harmful prompts


def test_breakdown_by_trigger():
    records = [
        {"gold": "should_comply", "pred": "refusal", "trigger_word": "kill"},
        {"gold": "should_comply", "pred": "compliance", "trigger_word": "attack"},
    ]
    bd = breakdown_by(records, "trigger_word")
    assert bd["kill"].false_refusal_rate == 1.0
    assert bd["attack"].false_refusal_rate == 0.0


def test_mean_std():
    m, sd = mean_std([0.2, 0.4, 0.6])
    assert abs(m - 0.4) < 1e-9
    assert sd > 0
