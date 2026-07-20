"""T3: decor + venue selection and its effect on option totals."""
from app.agents.decor import select_decor_and_venue
from app.agents.graph import plan


def _reqs(**over):
    base = {"event_type": "reception", "guest_count": 120, "budget": 200000,
            "dietary_restrictions": [], "cuisine_pref": "Indian"}
    base.update(over)
    return base


def test_decor_and_venue_scale_with_tier():
    ess = select_decor_and_venue("essential", 120)
    std = select_decor_and_venue("standard", 120)
    prem = select_decor_and_venue("premium", 120)
    assert ess["decor_cost"] <= std["decor_cost"] <= prem["decor_cost"]
    assert ess["venue_cost"] <= std["venue_cost"] <= prem["venue_cost"]


def test_venue_respects_capacity():
    fit = select_decor_and_venue("essential", 120)
    toobig = select_decor_and_venue("essential", 100000)  # nothing seats this
    assert fit["venue_name"]
    assert fit["venue_capacity"] >= 120
    assert toobig["venue_name"] == ""
    assert "No catalog venue" in toobig["venue_note"]


def test_total_includes_decor_and_venue():
    for o in plan(_reqs())["options"]:
        assert o["total_cost"] == round(o["food_cost"] + o["decor_cost"] + o["venue_cost"], 2)
        assert o["decor"]["name"]
        assert o["venue"]["name"]  # 120 guests fit a catalog venue


def test_totals_still_monotonic_with_decor_venue():
    opts = {o["tier"]: o for o in plan(_reqs())["options"]}
    assert opts["essential"]["total_cost"] <= opts["standard"]["total_cost"]
    assert opts["standard"]["total_cost"] <= opts["premium"]["total_cost"]
