"""MCP tools over the local database (T7).

Every agent data read goes through one of these typed tools. Each opens its own
session, maps rows to DTOs, and returns validated plain data — the agents never
see SQLAlchemy. Grouped by the plan's tool families: recipe (dishes), decor,
venue, price, and stock.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.pricing import cost_menu
from app.db.database import SessionLocal
from app.db.models import DecorPackage, Dish, DishIngredient, InventoryItem, Venue
from app.mcp.schemas import DecorDTO, DishDTO, IngredientLineDTO, StockLevelDTO, VenueDTO

_LOAD_INGREDIENTS = selectinload(Dish.ingredients).selectinload(DishIngredient.item)


def _dish_to_dto(dish: Dish) -> DishDTO:
    lines = [
        IngredientLineDTO(
            item=line.item.name,
            unit=line.item.unit,
            price_per_unit=line.item.price_per_unit,
            qty_per_serving=line.qty_per_serving,
            stock_qty=line.item.stock_qty,
            allergens=list(line.item.allergens or []),
        )
        for line in dish.ingredients
    ]
    allergens = sorted({a for line in lines for a in line.allergens})
    return DishDTO(
        id=dish.id, name=dish.name, cuisine=dish.cuisine, course=dish.course,
        diet_tags=list(dish.diet_tags or []), allergens=allergens, ingredients=lines,
    )


# --- recipe tool -----------------------------------------------------------
def get_dishes(course: Optional[str] = None) -> List[DishDTO]:
    """All catalog dishes (with priced recipes), optionally filtered by course."""
    with SessionLocal() as session:
        stmt = select(Dish).options(_LOAD_INGREDIENTS)
        if course:
            stmt = stmt.where(Dish.course == course)
        return [_dish_to_dto(d) for d in session.scalars(stmt).all()]


# --- decor tool ------------------------------------------------------------
def get_decor_packages() -> List[DecorDTO]:
    with SessionLocal() as session:
        rows = session.scalars(select(DecorPackage).order_by(DecorPackage.price)).all()
        return [DecorDTO(id=r.id, name=r.name, style=r.style, price=r.price,
                         description=r.description) for r in rows]


# --- venue tool ------------------------------------------------------------
def get_venues(min_capacity: int = 0) -> List[VenueDTO]:
    """Venues seating at least ``min_capacity`` guests, cheapest first."""
    with SessionLocal() as session:
        stmt = select(Venue).where(Venue.capacity >= min_capacity).order_by(Venue.price)
        rows = session.scalars(stmt).all()
        return [VenueDTO(id=r.id, name=r.name, style=r.style,
                         capacity=r.capacity, price=r.price) for r in rows]


# --- price tool ------------------------------------------------------------
def price_menu(dishes: List[DishDTO], guest_count: int, budget: float) -> Dict:
    """Cost a menu (deterministic) from tool-provided priced dishes."""
    return cost_menu(dishes, guest_count, budget)


# --- stock tool ------------------------------------------------------------
def get_stock(item_names: Optional[List[str]] = None) -> List[StockLevelDTO]:
    """Current on-hand stock levels, optionally restricted to given items."""
    with SessionLocal() as session:
        stmt = select(InventoryItem)
        if item_names:
            stmt = stmt.where(InventoryItem.name.in_(item_names))
        rows = session.scalars(stmt).all()
        return [StockLevelDTO(item=r.name, unit=r.unit, stock_qty=r.stock_qty) for r in rows]
