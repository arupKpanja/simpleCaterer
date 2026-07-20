"""T5: vendor agent + human approval gate (draft → pause → place/reject)."""
import pytest

from app.agents.graph import plan
from app.services.orders import approve_option
from app.services.persistence import save_event
from app.services.vendor import (
    NoDraftError,
    NotFoundError,
    decide_vendor_order,
    draft_vendor_order,
    get_vendor_order,
)


def _approved_order(**over):
    reqs = {"event_type": "reception", "guest_count": 120, "budget": 200000,
            "dietary_restrictions": ["vegetarian"], "cuisine_pref": "Indian"}
    reqs.update(over)
    options = plan(reqs)["options"]
    event_id = save_event(reqs, options)
    return approve_option(event_id, options[1]["id"])["order_id"]


def test_draft_pauses_at_gate_without_placing():
    order_id = _approved_order()
    draft = draft_vendor_order(order_id)
    assert draft["status"] == "awaiting_approval"
    assert draft["lines"]
    assert draft["total"] > 0
    # nothing is placed yet — DB status is still draft, no export list
    vo = get_vendor_order(order_id)
    assert vo["status"] == "draft"
    assert vo["shopping_list"] == []


def test_approve_places_order_and_exports_list():
    order_id = _approved_order()
    draft = draft_vendor_order(order_id)
    result = decide_vendor_order(order_id, "approve")
    assert result["status"] == "placed"
    assert result["decided_at"]
    assert result["shopping_list"]  # exportable list appears once placed
    assert result["total"] == draft["total"]
    assert get_vendor_order(order_id)["status"] == "placed"


def test_reject_cancels_order():
    order_id = _approved_order()
    draft_vendor_order(order_id)
    result = decide_vendor_order(order_id, "reject")
    assert result["status"] == "rejected"
    assert result["shopping_list"] == []
    assert get_vendor_order(order_id)["status"] == "rejected"


def test_decision_before_draft_errors():
    order_id = _approved_order()
    with pytest.raises(NoDraftError):
        decide_vendor_order(order_id, "approve")


def test_draft_is_idempotent():
    order_id = _approved_order()
    first = draft_vendor_order(order_id)
    second = draft_vendor_order(order_id)
    assert first["vendor_order_id"] == second["vendor_order_id"]


def test_draft_unknown_order_raises():
    with pytest.raises(NotFoundError):
        draft_vendor_order("not-a-real-order")


def test_decision_is_idempotent_after_placing():
    order_id = _approved_order()
    draft_vendor_order(order_id)
    decide_vendor_order(order_id, "approve")
    again = decide_vendor_order(order_id, "reject")  # ignored; already placed
    assert again["status"] == "placed"
