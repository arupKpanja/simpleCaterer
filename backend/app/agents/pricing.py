"""Deterministic costing tools — all catering arithmetic lives here.

Per the plan's risk mitigation, budget math is *never* done in the LLM. These
pure functions operate on the ``DishDTO`` objects supplied by the MCP tool layer
(so no database access happens here) and compute per-serving cost, an aggregated
priced shopping list, and the budget check.
"""
from __future__ import annotations

from typing import Dict, List

from app.mcp.schemas import DishDTO


def dish_serving_cost(dish: DishDTO) -> float:
    """Ingredient cost of a single serving of a dish."""
    return round(sum(line.qty_per_serving * line.price_per_unit
                     for line in dish.ingredients), 4)


def build_shopping_list(menu_dishes: List[DishDTO], guest_count: int) -> List[Dict]:
    """Aggregate every menu dish's ingredients into a priced shopping list."""
    agg: Dict[str, Dict] = {}
    for dish in menu_dishes:
        for line in dish.ingredients:
            entry = agg.setdefault(line.item, {
                "item": line.item,
                "unit": line.unit,
                "price_per_unit": line.price_per_unit,
                "qty": 0.0,
                "stock_qty": line.stock_qty,
                "allergens": line.allergens or [],
            })
            entry["qty"] += line.qty_per_serving * guest_count

    shopping = []
    for entry in agg.values():
        entry["qty"] = round(entry["qty"], 3)
        entry["line_cost"] = round(entry["qty"] * entry["price_per_unit"], 2)
        entry["short_by"] = round(max(0.0, entry["qty"] - entry["stock_qty"]), 3)
        shopping.append(entry)
    shopping.sort(key=lambda e: e["line_cost"], reverse=True)
    return shopping


def cost_menu(menu_dishes: List[DishDTO], guest_count: int, budget: float) -> Dict:
    """Full costing for a menu: shopping list, totals, and budget check."""
    shopping = build_shopping_list(menu_dishes, guest_count)
    subtotal = round(sum(e["line_cost"] for e in shopping), 2)
    per_guest = round(subtotal / guest_count, 2) if guest_count else 0.0
    within_budget = budget <= 0 or subtotal <= budget
    overage = round(max(0.0, subtotal - budget), 2) if budget > 0 else 0.0
    return {
        "shopping_list": shopping,
        "subtotal": subtotal,
        "per_guest": per_guest,
        "budget": budget,
        "within_budget": within_budget,
        "overage": overage,
    }
