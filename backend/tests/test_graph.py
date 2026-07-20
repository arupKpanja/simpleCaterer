"""End-to-end tests for the tiered planning graph (deterministic fallback path)."""
from app.agents.graph import plan, run_plan
from app.agents.tiers import TIERS


def _reqs(**over):
    base = {
        "event_type": "wedding reception",
        "guest_count": 120,
        "budget": 60000,
        "dietary_restrictions": [],
        "cuisine_pref": "Indian",
    }
    base.update(over)
    return base


def test_plan_produces_three_tiers():
    options = plan(_reqs())["options"]
    assert [o["tier"] for o in options] == TIERS  # sorted essential/standard/premium
    for o in options:
        assert o["courses"]
        assert o["total_cost"] > 0
        assert o["per_guest"] == round(o["total_cost"] / 120, 2)
        assert o["allergen_safe"] is True


def test_tiers_are_cost_monotonic():
    options = {o["tier"]: o for o in plan(_reqs())["options"]}
    assert options["essential"]["total_cost"] <= options["standard"]["total_cost"]
    assert options["standard"]["total_cost"] <= options["premium"]["total_cost"]


def test_vegetarian_plan_has_no_meat():
    for o in plan(_reqs(dietary_restrictions=["vegetarian"]))["options"]:
        dishes = {c["dish"] for c in o["courses"]}
        assert "Chicken Biryani" not in dishes
        for course in o["courses"]:
            assert "shellfish" not in course["allergens"]


def test_nut_allergy_plan_is_allergen_safe():
    for o in plan(_reqs(dietary_restrictions=["no nuts"]))["options"]:
        assert o["allergen_safe"] is True
        for course in o["courses"]:
            assert "nuts" not in course["allergens"]


def test_invalid_requirements_short_circuit():
    state = plan(_reqs(guest_count=0))
    assert state.get("errors")
    assert not state.get("options")


def test_stream_emits_stages_then_result():
    events = list(run_plan(_reqs()))
    assert events[-1]["type"] == "result"
    assert len(events[-1]["options"]) == 3
    stages = {e["stage"] for e in events if e["type"] == "stage"}
    assert "supervisor" in stages and "assemble" in stages
    assert {f"tier:{t}" for t in TIERS}.issubset(stages)
