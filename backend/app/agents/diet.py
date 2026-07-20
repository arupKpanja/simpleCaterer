"""Deterministic dietary-constraint parsing and dish filtering.

Allergen accuracy is safety-critical, so this is pure, testable Python — never
left to the LLM. Free-text restrictions are normalized into a required diet tag
set plus an excluded-allergen set, then dishes (``DishDTO`` from the MCP tool
layer) are filtered against them.
"""
from __future__ import annotations

from typing import Dict, List

from app.mcp.schemas import DishDTO

# Known allergens we tag inventory with.
KNOWN_ALLERGENS = {"nuts", "dairy", "gluten", "shellfish", "egg", "soy"}

# Phrases that map a restriction onto an excluded allergen.
_ALLERGEN_PHRASES = {
    "nut": "nuts", "nuts": "nuts", "peanut": "nuts", "tree nut": "nuts",
    "dairy": "dairy", "milk": "dairy", "lactose": "dairy",
    "gluten": "gluten", "wheat": "gluten",
    "shellfish": "shellfish", "prawn": "shellfish", "shrimp": "shellfish", "seafood": "shellfish",
    "egg": "egg", "soy": "soy", "soya": "soy",
}


def parse_restrictions(restrictions: List[str]) -> Dict[str, list]:
    """Normalize free-text restrictions into structured diet constraints."""
    required_diet_tags: set = set()
    excluded_allergens: set = set()

    for raw in restrictions or []:
        r = raw.strip().lower()
        if not r:
            continue
        if "vegan" in r:
            required_diet_tags.add("vegan")
        elif "veg" in r:  # vegetarian (also matches "pure veg")
            required_diet_tags.add("vegetarian")
        if "gluten" in r and ("free" in r or "no" in r or "without" in r):
            required_diet_tags.add("gluten-free")
        # allergen exclusions ("no nuts", "nut allergy", "without dairy", ...)
        for phrase, allergen in _ALLERGEN_PHRASES.items():
            if phrase in r:
                excluded_allergens.add(allergen)

    # A vegan menu is also vegetarian; don't require both tags explicitly.
    if "vegan" in required_diet_tags:
        required_diet_tags.discard("vegetarian")

    return {
        "required_diet_tags": sorted(required_diet_tags),
        "excluded_allergens": sorted(excluded_allergens),
    }


def dish_satisfies(dish: DishDTO, diet: Dict[str, list]) -> bool:
    """True iff the dish meets every required diet tag and carries no excluded allergen."""
    tags = set(dish.diet_tags or [])
    for required in diet.get("required_diet_tags", []):
        if required not in tags:
            return False
    dish_allergens = set(dish.allergens)  # derived from ingredients
    if dish_allergens & set(diet.get("excluded_allergens", [])):
        return False
    return True


def filter_dishes(dishes: List[DishDTO], diet: Dict[str, list]) -> List[DishDTO]:
    return [d for d in dishes if dish_satisfies(d, diet)]
