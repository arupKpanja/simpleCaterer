"""T1: persisting an option set and reading it back."""
from app.agents.graph import plan
from app.services.persistence import get_event, save_event


def _reqs(**over):
    base = {
        "event_type": "wedding reception", "guest_count": 120, "budget": 60000,
        "dietary_restrictions": ["vegetarian"], "cuisine_pref": "Indian",
    }
    base.update(over)
    return base


def test_save_and_fetch_roundtrip():
    reqs = _reqs()
    options = plan(reqs)["options"]
    event_id = save_event(reqs, options)
    assert event_id

    stored = get_event(event_id)
    assert stored is not None
    assert stored["event_id"] == event_id
    assert stored["requirements"]["guest_count"] == 120
    assert len(stored["options"]) == len(options) == 3

    src = {o["tier"]: o for o in options}
    for saved_opt in stored["options"]:
        original = src[saved_opt["tier"]]
        assert saved_opt["total_cost"] == original["total_cost"]
        assert {c["dish"] for c in saved_opt["courses"]} == {c["dish"] for c in original["courses"]}
        assert saved_opt["allergen_safe"] is True


def test_save_event_backfills_option_ids():
    reqs = _reqs()
    options = plan(reqs)["options"]
    save_event(reqs, options)
    # ids are assigned at persist time and written back so callers can approve them
    assert all(o.get("id") for o in options)


def test_get_missing_event_returns_none():
    assert get_event("does-not-exist") is None


def test_menu_item_snapshot_preserves_allergens():
    reqs = _reqs(dietary_restrictions=["no nuts"])
    options = plan(reqs)["options"]
    stored = get_event(save_event(reqs, options))
    for opt in stored["options"]:
        for course in opt["courses"]:
            assert "nuts" not in course["allergens"]
