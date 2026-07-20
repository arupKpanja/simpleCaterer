"""Vendor agent + human approval gate (T5).

A small LangGraph flow drafts a supplier order from a frozen approved order,
then **pauses at a human approval gate** (``interrupt_before=["place"]``) so
nothing is placed without sign-off. On resume the owner's decision either places
the order (status ``placed``, with an exportable shopping list) or rejects it.
The gate resumes on the same durable checkpointer built in T6.

There is no supplier API (local-only), so "placing" records the order and
produces the shopping list the owner acts on manually.
"""
from __future__ import annotations

import operator
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.checkpointer import get_checkpointer
from app.db.database import SessionLocal
from app.db.models import ApprovedOrder, InventoryItem, OrderLine, VendorOrder


class VendorError(Exception):
    """Base for vendor-flow errors."""


class NotFoundError(VendorError):
    pass


class NoDraftError(VendorError):
    pass


class VendorState(TypedDict, total=False):
    approved_order_id: str
    decision: str            # "approve" | "reject" (set on resume)
    vendor_order_id: str
    draft: Dict
    result: Dict
    log: Annotated[List[str], operator.add]


# --------------------------------------------------------------------------
# DB helpers
# --------------------------------------------------------------------------
def _draft_from_approved(approved_order_id: str) -> Dict:
    """Create (or return the existing) draft vendor order for an approved order."""
    with SessionLocal() as session:
        approved = session.get(ApprovedOrder, approved_order_id)
        if approved is None:
            raise NotFoundError("approved order not found")

        existing = (
            session.query(VendorOrder)
            .filter(VendorOrder.approved_order_id == approved_order_id)
            .one_or_none()
        )
        if existing is not None:
            return _vendor_to_dict(existing)

        shopping = approved.snapshot.get("shopping_list", []) or []
        vo = VendorOrder(approved_order_id=approved_order_id, status="draft",
                         total=round(sum(l.get("line_cost", 0.0) for l in shopping), 2))
        session.add(vo)
        session.flush()
        for line in shopping:
            session.add(OrderLine(
                vendor_order_id=vo.id,
                item_name=line.get("item", ""),
                unit=line.get("unit", ""),
                qty=line.get("qty", 0.0),
                unit_price=line.get("price_per_unit", 0.0),
                line_cost=line.get("line_cost", 0.0),
            ))
        session.commit()
        return _vendor_to_dict(vo)


def _deduct_stock(session, lines) -> list:
    """Consume on-hand stock for a placed order; return the per-item impact.

    Each item's stock drops by what the event consumes (min of required and what
    is on hand); anything beyond stock is the shortfall that had to be purchased.
    Runs once, inside the draft→placed transition, so it is not double-applied.
    """
    items = {i.name: i for i in session.scalars(select(InventoryItem)).all()}
    impact = []
    for line in lines:
        item = items.get(line.item_name)
        before = item.stock_qty if item else 0.0
        consumed = min(line.qty, before)
        short_by = round(max(0.0, line.qty - before), 3)
        if item:
            item.stock_qty = round(before - consumed, 3)
        impact.append({
            "item": line.item_name,
            "required": line.qty,
            "consumed": round(consumed, 3),
            "short_by": short_by,
            "stock_after": item.stock_qty if item else 0.0,
        })
    return impact


def _decide(vendor_order_id: str, decision: str) -> Dict:
    """Apply the human decision: place (deducting stock) or reject the draft."""
    with SessionLocal() as session:
        vo = session.get(VendorOrder, vendor_order_id,
                         options=[selectinload(VendorOrder.lines)])
        if vo is None:
            raise NotFoundError("vendor order not found")
        if vo.status == "draft":
            if decision == "approve":
                vo.status = "placed"
                vo.stock_impact = _deduct_stock(session, vo.lines)
            else:
                vo.status = "rejected"
            vo.decided_at = datetime.now(timezone.utc)
            session.commit()
        return _vendor_to_dict(vo)


def _vendor_to_dict(vo: VendorOrder) -> Dict:
    lines = [{
        "item": l.item_name, "unit": l.unit, "qty": l.qty,
        "unit_price": l.unit_price, "line_cost": l.line_cost,
    } for l in vo.lines]
    return {
        "vendor_order_id": vo.id,
        "approved_order_id": vo.approved_order_id,
        "status": vo.status,
        "total": vo.total,
        "created_at": vo.created_at.isoformat(),
        "decided_at": vo.decided_at.isoformat() if vo.decided_at else None,
        "lines": lines,
        # stock consumed when placed (per-item, with shortfalls flagged)
        "stock_impact": vo.stock_impact or [],
        # exportable shopping list is meaningful once placed
        "shopping_list": lines if vo.status == "placed" else [],
    }


# --------------------------------------------------------------------------
# Graph: draft -> [approval gate] -> place
# --------------------------------------------------------------------------
def _draft_node(state: VendorState) -> Dict:
    draft = _draft_from_approved(state["approved_order_id"])
    return {"vendor_order_id": draft["vendor_order_id"], "draft": draft,
            "log": [f"Drafted vendor order {draft['vendor_order_id']} "
                    f"({len(draft['lines'])} lines, total {draft['total']}); awaiting approval."]}


def _place_node(state: VendorState) -> Dict:
    decision = state.get("decision", "reject")
    result = _decide(state["vendor_order_id"], decision)
    verb = "Placed" if result["status"] == "placed" else "Rejected"
    return {"result": result, "log": [f"{verb} vendor order {result['vendor_order_id']}."]}


@lru_cache(maxsize=1)
def get_vendor_graph():
    # Node names must not collide with VendorState keys (LangGraph rule).
    g = StateGraph(VendorState)
    g.add_node("drafting", _draft_node)
    g.add_node("placing", _place_node)
    g.add_edge(START, "drafting")
    g.add_edge("drafting", "placing")
    g.add_edge("placing", END)
    # Pause before placing — the human approval gate.
    return g.compile(checkpointer=get_checkpointer(), interrupt_before=["placing"])


def _config(approved_order_id: str) -> Dict:
    return {"configurable": {"thread_id": f"vendor-{approved_order_id}"}}


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def draft_vendor_order(approved_order_id: str) -> Dict:
    """Run the flow up to the approval gate; returns the draft awaiting approval."""
    # Validate up front so a bad id is a clean 404 (not a graph error).
    if get_order_exists(approved_order_id) is False:
        raise NotFoundError("approved order not found")

    graph = get_vendor_graph()
    config = _config(approved_order_id)

    snap = graph.get_state(config)
    if snap and snap.values.get("result"):
        return snap.values["result"]  # already decided (status placed/rejected)
    if snap and snap.values.get("draft"):
        # already drafted and paused at the gate — don't re-run
        return {**snap.values["draft"], "status": "awaiting_approval"}

    graph.invoke({"approved_order_id": approved_order_id}, config)
    state = graph.get_state(config).values
    return {**state["draft"], "status": "awaiting_approval"}


def decide_vendor_order(approved_order_id: str, decision: str) -> Dict:
    """Resume the paused flow with the human decision (approve/reject)."""
    if decision not in ("approve", "reject"):
        raise VendorError("decision must be 'approve' or 'reject'")

    graph = get_vendor_graph()
    config = _config(approved_order_id)

    snap = graph.get_state(config)
    if snap is None or not snap.values.get("vendor_order_id"):
        raise NoDraftError("no draft to decide on; draft the vendor order first")
    if snap.values.get("result"):
        return snap.values["result"]  # already decided (idempotent)

    graph.update_state(config, {"decision": decision})
    graph.invoke(None, config)
    return graph.get_state(config).values["result"]


def get_vendor_order(approved_order_id: str) -> Optional[Dict]:
    with SessionLocal() as session:
        vo = (
            session.query(VendorOrder)
            .filter(VendorOrder.approved_order_id == approved_order_id)
            .one_or_none()
        )
        if vo is None:
            return None
        # eager-load lines within the session
        _ = vo.lines
        return _vendor_to_dict(vo)


def get_order_exists(approved_order_id: str) -> bool:
    with SessionLocal() as session:
        return session.get(ApprovedOrder, approved_order_id) is not None
