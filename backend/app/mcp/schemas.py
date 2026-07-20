"""Typed DTOs returned by the MCP tool layer.

These are plain, validated data objects (no ORM, no live session) so the agents
depend on a stable contract rather than database internals.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class IngredientLineDTO(BaseModel):
    item: str
    unit: str
    price_per_unit: float
    qty_per_serving: float
    stock_qty: float
    allergens: List[str] = []


class DishDTO(BaseModel):
    id: int
    name: str
    cuisine: str
    course: str
    diet_tags: List[str] = []
    allergens: List[str] = []  # derived union of ingredient allergens
    ingredients: List[IngredientLineDTO] = []


class DecorDTO(BaseModel):
    id: int
    name: str
    style: str
    price: float
    description: str = ""


class VenueDTO(BaseModel):
    id: int
    name: str
    style: str
    capacity: int
    price: float


class StockLevelDTO(BaseModel):
    item: str
    unit: str
    stock_qty: float
