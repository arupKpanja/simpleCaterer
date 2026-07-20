"""T8: placing a vendor order deducts consumed stock and flags shortfalls."""
from app.agents.graph import plan
from app.mcp import tools
from app.services.orders import approve_option
from app.services.persistence import save_event
from app.services.vendor import decide_vendor_order, draft_vendor_order, get_vendor_order


def _placed_order(**over):
    reqs = {"event_type": "reception", "guest_count": 120, "budget": 200000,
            "dietary_restrictions": ["vegetarian"], "cuisine_pref": "Indian"}
    reqs.update(over)
    options = plan(reqs)["options"]
    event_id = save_event(reqs, options)
    order_id = approve_option(event_id, options[1]["id"])["order_id"]
    draft = draft_vendor_order(order_id)
    return order_id, draft


def _stock_map():
    return {s.item: s.stock_qty for s in tools.get_stock()}


def test_placing_deducts_stock():
    order_id, draft = _placed_order()
    before = _stock_map()
    result = decide_vendor_order(order_id, "approve")

    assert result["stock_impact"]
    after = _stock_map()
    for entry in result["stock_impact"]:
        item = entry["item"]
        # stock dropped by exactly what was consumed
        assert round(before[item] - entry["consumed"], 3) == after[item]
        assert after[item] >= 0
        # consumed + short_by covers the full requirement
        assert round(entry["consumed"] + entry["short_by"], 3) == round(entry["required"], 3)


def test_rejecting_does_not_touch_stock():
    order_id, _ = _placed_order()
    before = _stock_map()
    result = decide_vendor_order(order_id, "reject")
    assert result["stock_impact"] == []
    assert _stock_map() == before


def test_deduction_is_not_double_applied():
    order_id, _ = _placed_order()
    decide_vendor_order(order_id, "approve")
    after_first = _stock_map()
    decide_vendor_order(order_id, "approve")  # idempotent — no further deduction
    assert _stock_map() == after_first


def test_shortfall_flagged_when_stock_insufficient():
    # A huge guest count forces demand well past on-hand stock.
    order_id, _ = _placed_order(guest_count=5000, budget=10_000_000)
    result = decide_vendor_order(order_id, "approve")
    assert any(e["short_by"] > 0 for e in result["stock_impact"])
    # every item is drawn down to zero when short
    for e in result["stock_impact"]:
        if e["short_by"] > 0:
            assert e["stock_after"] == 0.0
