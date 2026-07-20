"""Approved-order freeze (T4).

Freezing turns a chosen option into an immutable ``ApprovedOrder`` with a full
JSON snapshot — the contract Part 2 (event-day ops) will read against. Exactly
one approved order per event.
"""
from __future__ import annotations

from typing import Dict, Optional

from sqlalchemy.orm import selectinload

from app.db.database import SessionLocal
from app.db.models import ApprovedOrder, Option
from app.services.persistence import _option_to_dict


class OrderError(Exception):
    """Base for approval errors."""


class NotFoundError(OrderError):
    """Event/option not found or the option doesn't belong to the event."""


class AlreadyApprovedError(OrderError):
    """The event already has a frozen approved order."""

    def __init__(self, order_id: str):
        super().__init__("event already has an approved order")
        self.order_id = order_id


def _order_to_dict(order: ApprovedOrder) -> Dict:
    return {
        "order_id": order.id,
        "event_id": order.event_id,
        "option_id": order.option_id,
        "tier": order.tier,
        "status": order.status,
        "total_cost": order.total_cost,
        "per_guest": order.per_guest,
        "guest_count": order.guest_count,
        "approved_at": order.approved_at.isoformat(),
        "snapshot": order.snapshot,
    }


def approve_option(event_id: str, option_id: str) -> Dict:
    """Freeze the chosen option for an event. Raises OrderError subclasses."""
    with SessionLocal() as session:
        option = session.get(
            Option, option_id,
            options=[selectinload(Option.menu_items)],
        )
        if option is None or option.event_id != event_id:
            raise NotFoundError("option not found for this event")

        existing = (
            session.query(ApprovedOrder)
            .filter(ApprovedOrder.event_id == event_id)
            .one_or_none()
        )
        if existing is not None:
            raise AlreadyApprovedError(existing.id)

        snapshot = _option_to_dict(option)
        order = ApprovedOrder(
            event_id=event_id,
            option_id=option.id,
            tier=option.tier,
            status="approved",
            total_cost=option.total_cost,
            per_guest=option.per_guest,
            guest_count=option.event.guest_count,  # guest_count lives on the Event
            snapshot=snapshot,
        )
        session.add(order)
        session.commit()
        return _order_to_dict(order)


def get_order(order_id: str) -> Optional[Dict]:
    with SessionLocal() as session:
        order = session.get(ApprovedOrder, order_id)
        return _order_to_dict(order) if order else None


def get_order_for_event(event_id: str) -> Optional[Dict]:
    with SessionLocal() as session:
        order = (
            session.query(ApprovedOrder)
            .filter(ApprovedOrder.event_id == event_id)
            .one_or_none()
        )
        return _order_to_dict(order) if order else None
