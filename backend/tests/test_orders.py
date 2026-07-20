"""T4: freezing a chosen option into an immutable approved order."""
import pytest

from app.agents.graph import plan
from app.services.orders import (
    AlreadyApprovedError,
    NotFoundError,
    approve_option,
    get_order,
    get_order_for_event,
)
from app.services.persistence import save_event


def _reqs(**over):
    base = {"event_type": "reception", "guest_count": 120, "budget": 200000,
            "dietary_restrictions": ["vegetarian"], "cuisine_pref": "Indian"}
    base.update(over)
    return base


def _fresh_event():
    reqs = _reqs()
    options = plan(reqs)["options"]
    event_id = save_event(reqs, options)
    stored = save_event  # noqa: F841 (silence linters about unused)
    from app.services.persistence import get_event
    return event_id, get_event(event_id)["options"]


def test_approve_freezes_snapshot():
    event_id, options = _fresh_event()
    standard = next(o for o in options if o["tier"] == "standard")

    order = approve_option(event_id, standard["id"])
    assert order["order_id"]
    assert order["status"] == "approved"
    assert order["tier"] == "standard"
    assert order["total_cost"] == standard["total_cost"]
    assert order["guest_count"] == 120
    # snapshot is a full frozen copy of the option
    assert order["snapshot"]["courses"] == standard["courses"]
    assert order["snapshot"]["venue"]["name"] == standard["venue"]["name"]

    # retrievable by id and by event
    assert get_order(order["order_id"])["order_id"] == order["order_id"]
    assert get_order_for_event(event_id)["order_id"] == order["order_id"]


def test_second_approval_conflicts():
    event_id, options = _fresh_event()
    approve_option(event_id, options[0]["id"])
    with pytest.raises(AlreadyApprovedError):
        approve_option(event_id, options[1]["id"])


def test_option_must_belong_to_event():
    event_id, _ = _fresh_event()
    with pytest.raises(NotFoundError):
        approve_option(event_id, "not-a-real-option")


def test_snapshot_is_immutable_after_replan():
    """Re-planning the same requirements must not change an existing frozen order."""
    event_id, options = _fresh_event()
    order = approve_option(event_id, options[0]["id"])
    frozen_total = order["total_cost"]
    # a fresh planning run / new event does not touch the frozen snapshot
    _fresh_event()
    assert get_order(order["order_id"])["total_cost"] == frozen_total
