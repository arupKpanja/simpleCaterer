"""Labeled evaluation scenarios.

Each scenario carries its own *expected* constraints (not derived from the
parser), so the eval also catches restriction-parsing regressions. ``budget``
values are chosen to exercise both the within-budget and over-budget-flagged
paths.
"""
from __future__ import annotations

from typing import Dict, List

# name, requirements, expected required_diet_tags, expected excluded_allergens
SCENARIOS: List[Dict] = [
    {
        "name": "vegetarian wedding",
        "requirements": {"event_type": "wedding", "guest_count": 150, "budget": 300000,
                         "dietary_restrictions": ["vegetarian"], "cuisine_pref": "Indian"},
        "required_diet_tags": ["vegetarian"],
        "excluded_allergens": [],
    },
    {
        "name": "vegan gala",
        "requirements": {"event_type": "gala", "guest_count": 100, "budget": 300000,
                         "dietary_restrictions": ["vegan"], "cuisine_pref": "Indian"},
        "required_diet_tags": ["vegan"],
        "excluded_allergens": [],
    },
    {
        "name": "nut allergy reception",
        "requirements": {"event_type": "reception", "guest_count": 120, "budget": 300000,
                         "dietary_restrictions": ["nut allergy"]},
        "required_diet_tags": [],
        "excluded_allergens": ["nuts"],
    },
    {
        "name": "dairy-free vegetarian",
        "requirements": {"event_type": "lunch", "guest_count": 80, "budget": 300000,
                         "dietary_restrictions": ["vegetarian", "no dairy"]},
        "required_diet_tags": ["vegetarian"],
        "excluded_allergens": ["dairy"],
    },
    {
        "name": "shellfish allergy dinner",
        "requirements": {"event_type": "dinner", "guest_count": 60, "budget": 300000,
                         "dietary_restrictions": ["seafood allergy"]},
        "required_diet_tags": [],
        "excluded_allergens": ["shellfish"],
    },
    {
        "name": "gluten-free party",
        "requirements": {"event_type": "party", "guest_count": 90, "budget": 300000,
                         "dietary_restrictions": ["gluten free"]},
        "required_diet_tags": ["gluten-free"],
        "excluded_allergens": [],
    },
    {
        "name": "vegan no-nuts combo",
        "requirements": {"event_type": "conference", "guest_count": 200, "budget": 500000,
                         "dietary_restrictions": ["vegan", "no nuts"], "cuisine_pref": "Indian"},
        "required_diet_tags": ["vegan"],
        "excluded_allergens": ["nuts"],
    },
    {
        "name": "no restrictions, no budget cap",
        "requirements": {"event_type": "birthday", "guest_count": 50, "budget": 0,
                         "dietary_restrictions": []},
        "required_diet_tags": [],
        "excluded_allergens": [],
    },
    {
        "name": "tight budget forces overage flag",
        "requirements": {"event_type": "reception", "guest_count": 300, "budget": 30000,
                         "dietary_restrictions": ["vegetarian"], "cuisine_pref": "Indian"},
        "required_diet_tags": ["vegetarian"],
        "excluded_allergens": [],
    },
    {
        "name": "dairy + nut allergy",
        "requirements": {"event_type": "reception", "guest_count": 100, "budget": 300000,
                         "dietary_restrictions": ["no dairy", "no nuts"]},
        "required_diet_tags": [],
        "excluded_allergens": ["dairy", "nuts"],
    },
]
