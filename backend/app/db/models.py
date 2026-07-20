"""ORM models for the Part 1 planning/quoting catalog.

Scope note: the dish catalog + priced inventory feed the Menu&Diet and
Inventory&Cost agents; the Event/Option/OptionMenuItem tables persist the option
sets those agents produce (T1). Approved-order / vendor / event-day tables arrive
in later phases.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InventoryItem(Base):
    """A priced raw material held in local stock (an ingredient line item)."""

    __tablename__ = "inventory_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # kg, litre, unit, ...
    price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    stock_qty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # allergen tags carried by this raw material, e.g. ["nuts", "dairy"]
    allergens: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    lines: Mapped[List["DishIngredient"]] = relationship(back_populates="item")


class Dish(Base):
    """A catalog dish the Menu&Diet agent can choose from."""

    __tablename__ = "dish"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    cuisine: Mapped[str] = mapped_column(String(60), nullable=False)
    course: Mapped[str] = mapped_column(String(30), nullable=False)  # starter/main/side/dessert
    # diet tags this dish satisfies, e.g. ["vegetarian", "vegan", "gluten-free"]
    diet_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    ingredients: Mapped[List["DishIngredient"]] = relationship(
        back_populates="dish", cascade="all, delete-orphan"
    )

    @property
    def allergens(self) -> List[str]:
        """Allergens are derived from the dish's ingredients (safety-critical)."""
        found = set()
        for line in self.ingredients:
            found.update(line.item.allergens or [])
        return sorted(found)


class DishIngredient(Base):
    """Recipe line: how much of an inventory item one serving of a dish needs."""

    __tablename__ = "dish_ingredient"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dish.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_item.id"), nullable=False)
    qty_per_serving: Mapped[float] = mapped_column(Float, nullable=False)

    dish: Mapped["Dish"] = relationship(back_populates="ingredients")
    item: Mapped["InventoryItem"] = relationship(back_populates="lines")


# --------------------------------------------------------------------------
# Persisted planning output (T1). An Event groups the option set produced for
# one planning session; each Option holds its costed menu as OptionMenuItems.
# --------------------------------------------------------------------------
class Event(Base):
    """One planning session's requirements; groups the options offered for it."""

    __tablename__ = "event"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dietary_restrictions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    cuisine_pref: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    event_date: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    options: Mapped[List["Option"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Option(Base):
    """A single costed option (tier) offered for an event."""

    __tablename__ = "option"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("event.id"), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)
    theme: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    # cost breakdown: total_cost = food_cost + decor_cost + venue_cost
    food_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    decor_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    venue_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    per_guest: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    within_budget: Mapped[bool] = mapped_column(default=True, nullable=False)
    overage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    allergen_safe: Mapped[bool] = mapped_column(default=True, nullable=False)
    # chosen decor package + venue (snapshots; nullable when none fits)
    decor_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    venue_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    # denormalized shopping list kept with the option for quick retrieval/export
    shopping_list: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="options")
    menu_items: Mapped[List["OptionMenuItem"]] = relationship(
        back_populates="option", cascade="all, delete-orphan"
    )


class ApprovedOrder(Base):
    """An immutable freeze of the option the client chose (T4).

    Holds a full JSON snapshot of the option at approval time so it stays fixed
    even if the catalog or options change afterwards — this is the contract the
    Part 2 event-day operations read against. One approved order per event.
    """

    __tablename__ = "approved_order"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("event.id"), unique=True, nullable=False)
    option_id: Mapped[str] = mapped_column(ForeignKey("option.id"), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="approved", nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    per_guest: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    # frozen copy of the chosen option (menu, decor, venue, shopping list, ...)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class VendorOrder(Base):
    """A supplier order drafted from an approved order (T5).

    Passes through a human approval gate: ``draft`` → ``placed`` or ``rejected``.
    One vendor order per approved order in the MVP.
    """

    __tablename__ = "vendor_order"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    approved_order_id: Mapped[str] = mapped_column(
        ForeignKey("approved_order.id"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # per-item stock consumption recorded when the order is placed (T8)
    stock_impact: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    lines: Mapped[List["OrderLine"]] = relationship(
        back_populates="vendor_order", cascade="all, delete-orphan"
    )


class OrderLine(Base):
    """One purchasable line of a vendor order."""

    __tablename__ = "order_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_order_id: Mapped[str] = mapped_column(ForeignKey("vendor_order.id"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(160), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    qty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    line_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    vendor_order: Mapped["VendorOrder"] = relationship(back_populates="lines")


class OptionMenuItem(Base):
    """One course of an option's menu (a snapshot of the chosen dish)."""

    __tablename__ = "option_menu_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    option_id: Mapped[str] = mapped_column(ForeignKey("option.id"), nullable=False)
    course: Mapped[str] = mapped_column(String(30), nullable=False)
    dish_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dish_name: Mapped[str] = mapped_column(String(160), nullable=False)
    cuisine: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    diet_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    allergens: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    serving_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    option: Mapped["Option"] = relationship(back_populates="menu_items")


# --------------------------------------------------------------------------
# Decor & Venue catalog (T3). Priced locally; the Decor & Venue agent selects
# a package + a capacity-fitting venue per tier.
# --------------------------------------------------------------------------
class DecorPackage(Base):
    """A priced decor package (flowers, lighting, stage, table settings)."""

    __tablename__ = "decor_package"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    style: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)  # flat package price
    description: Mapped[str] = mapped_column(String(300), default="", nullable=False)


class Venue(Base):
    """A bookable venue with a guest capacity and hire cost."""

    __tablename__ = "venue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    style: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)  # flat hire cost
