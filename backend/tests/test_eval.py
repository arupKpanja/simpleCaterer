"""T9: the eval harness gates on the plan's success metrics."""
from app.eval.run import BUDGET_THRESHOLD, DIET_THRESHOLD, evaluate


def test_eval_meets_thresholds():
    report = evaluate()
    assert report["options_scored"] > 0
    assert report["diet_compliance_rate"] >= DIET_THRESHOLD, report["failures"]
    assert report["budget_ok_rate"] >= BUDGET_THRESHOLD, report["failures"]


def test_eval_exercises_overage_flag():
    """The dataset must actually include an over-budget (flagged) case."""
    from app.agents.graph import plan
    from app.eval.dataset import SCENARIOS

    tight = next(s for s in SCENARIOS if "overage" in s["name"])
    options = plan(tight["requirements"])["options"]
    assert any(not o["within_budget"] and o["overage"] > 0 for o in options)
