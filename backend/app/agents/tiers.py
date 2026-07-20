"""Per-tier planning worker (the fan-out target).

The supervisor dispatches one ``plan_tier`` invocation per tier via ``Send``.
Each worker builds a diet-compliant menu for its tier, prices it, runs the
allergen post-check, and emits one costed option into the shared ``options``
channel.

Tier strategy (deterministic — tools decide): candidates per course are ranked
by serving cost, then **essential** takes the cheapest, **premium** the priciest,
and **standard** the middle. This guarantees premium >= standard >= essential in
cost while keeping the three menus visibly distinct. The LLM only names the
theme (model proposes), never the selection or the arithmetic.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from app.agents.decor import select_decor_and_venue
from app.agents.diet import filter_dishes
from app.agents.pricing import dish_serving_cost
from app.agents.state import EventState, log_entry
from app.llm.client import llm
from app.mcp import tools
from app.mcp.schemas import DishDTO

log = logging.getLogger("caterer.tiers")

TIERS = ["essential", "standard", "premium"]
COURSE_ORDER = ["starter", "main", "side", "dessert"]


def _candidates_by_course(diet: Dict) -> Dict[str, List[DishDTO]]:
    """Diet-compliant dishes grouped by course, each list ranked by serving cost."""
    allowed = filter_dishes(tools.get_dishes(), diet)
    grouped: Dict[str, List[DishDTO]] = {}
    for course in COURSE_ORDER:
        cands = sorted((d for d in allowed if d.course == course), key=dish_serving_cost)
        if cands:
            grouped[course] = cands
    return grouped


def _pick_for_tier(cands: List[DishDTO], tier: str) -> DishDTO:
    if tier == "essential":
        return cands[0]
    if tier == "premium":
        return cands[-1]
    return cands[len(cands) // 2]  # standard


def _theme_name(tier: str, reqs: Dict, dishes: List[DishDTO]) -> str:
    cuisine = reqs.get("cuisine_pref") or (dishes[0].cuisine if dishes else "Signature")
    fallback = f"{tier.capitalize()} {cuisine} {reqs.get('event_type', 'menu')}".strip()
    if not llm.is_available():
        return fallback
    names = ", ".join(d.name for d in dishes)
    prompt = (
        f"Give a short, appealing 3-6 word theme name for a {tier}-tier catering "
        f"menu for a {reqs.get('event_type', 'event')} featuring: {names}. "
        'Respond as JSON: {"theme": "..."}.'
    )
    data = llm.complete_json(prompt, system="You name catering menus. Output only JSON.")
    if data and str(data.get("theme", "")).strip():
        return str(data["theme"]).strip()
    return fallback


def plan_tier(state: EventState) -> Dict:
    """Build, price, and check one tier's option. Runs in parallel per tier."""
    reqs = state["requirements"]
    diet = state.get("diet", {})
    tier = state["tier"]
    guests = int(reqs.get("guest_count", 0) or 0)
    budget = float(reqs.get("budget", 0) or 0)

    grouped = _candidates_by_course(diet)
    if not grouped:
        return {"log": log_entry(f"tier:{tier}",
                                 f"No diet-compliant dishes for the {tier} tier.")}

    picks = {course: _pick_for_tier(cands, tier) for course, cands in grouped.items()}
    selected = [picks[c] for c in COURSE_ORDER if c in picks]

    # price tool: costing/shopping list from tool-provided priced dishes.
    cost = tools.price_menu(selected, guests, budget)

    # Decor & Venue agent: package + capacity-fitting venue for this tier.
    dv = select_decor_and_venue(tier, guests)

    # Safety-critical allergen post-check on the assembled menu.
    excluded = set(diet.get("excluded_allergens", []))
    violations = [f"{d.name} contains {', '.join(sorted(set(d.allergens) & excluded))}"
                  for d in selected if set(d.allergens) & excluded]
    allergen_safe = not violations

    theme = _theme_name(tier, reqs, selected)
    courses = [{
        "course": c,
        "dish_id": picks[c].id,
        "dish": picks[c].name,
        "cuisine": picks[c].cuisine,
        "diet_tags": list(picks[c].diet_tags or []),
        "allergens": picks[c].allergens,
        "serving_cost": dish_serving_cost(picks[c]),
    } for c in COURSE_ORDER if c in picks]

    # Grand total folds food + decor + venue; budget check is against the total.
    food_cost = cost["subtotal"]
    total_cost = round(food_cost + dv["decor_cost"] + dv["venue_cost"], 2)
    within_budget = budget <= 0 or total_cost <= budget
    overage = round(max(0.0, total_cost - budget), 2) if budget > 0 else 0.0

    option = {
        "tier": tier,
        "theme": theme,
        "event_type": reqs.get("event_type"),
        "guest_count": guests,
        "courses": courses,
        "decor": {"name": dv["decor_name"], "style": dv["decor_style"],
                  "cost": dv["decor_cost"]},
        "venue": {"name": dv["venue_name"], "capacity": dv["venue_capacity"],
                  "cost": dv["venue_cost"], "note": dv["venue_note"]},
        "food_cost": food_cost,
        "decor_cost": dv["decor_cost"],
        "venue_cost": dv["venue_cost"],
        "total_cost": total_cost,
        "per_guest": round(total_cost / guests, 2) if guests else 0.0,
        "budget": budget,
        "within_budget": within_budget,
        "overage": overage,
        "allergen_safe": allergen_safe,
        "dietary_restrictions": reqs.get("dietary_restrictions", []),
        "shopping_list": cost["shopping_list"],
    }

    budget_note = ""
    if budget > 0:
        budget_note = " within budget" if within_budget else f" OVER budget by {overage}"
    venue_label = dv["venue_name"] or "no venue"
    result: Dict = {
        "options": [option],
        "log": log_entry(f"tier:{tier}",
                         f"'{theme}' ({tier}) — {len(courses)} courses + {dv['decor_name']} "
                         f"decor + {venue_label}; total {total_cost} "
                         f"({option['per_guest']}/guest){budget_note}."),
    }
    if violations:
        result["errors"] = ["ALLERGEN VIOLATION (" + tier + "): " + "; ".join(violations)]
    return result
