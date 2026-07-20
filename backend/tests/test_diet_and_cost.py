"""Unit tests for the safety-critical diet filter and deterministic costing.

Dishes come through the MCP tool layer as DTOs — the same path the agents use.
"""
from app.agents.diet import KNOWN_ALLERGENS, dish_satisfies, parse_restrictions
from app.agents.pricing import cost_menu, dish_serving_cost
from app.mcp import tools


def _dishes():
    return tools.get_dishes()


def test_parse_restrictions_vegan_and_nuts():
    diet = parse_restrictions(["vegan", "no nuts"])
    assert "vegan" in diet["required_diet_tags"]
    assert "vegetarian" not in diet["required_diet_tags"]  # vegan subsumes veg
    assert "nuts" in diet["excluded_allergens"]


def test_parse_restrictions_variants():
    assert "dairy" in parse_restrictions(["lactose intolerant"])["excluded_allergens"]
    assert "shellfish" in parse_restrictions(["seafood allergy"])["excluded_allergens"]
    assert "gluten-free" in parse_restrictions(["gluten free please"])["required_diet_tags"]


def test_vegetarian_filter_excludes_meat_dishes():
    diet = parse_restrictions(["vegetarian"])
    kept = [d for d in _dishes() if dish_satisfies(d, diet)]
    names = {d.name for d in kept}
    assert "Chicken Biryani" not in names
    assert "Veg Biryani" in names


def test_nut_allergy_excludes_cashew_dishes():
    diet = parse_restrictions(["nut allergy"])
    for d in _dishes():
        if dish_satisfies(d, diet):
            assert "nuts" not in d.allergens, f"{d.name} slipped through nut filter"


def test_serving_cost_positive():
    for d in _dishes():
        assert dish_serving_cost(d) > 0


def test_cost_menu_budget_flags_overage():
    dishes = _dishes()[:3]
    result = cost_menu(dishes, guest_count=100, budget=1.0)  # absurdly low budget
    assert result["within_budget"] is False
    assert result["overage"] > 0
    assert result["subtotal"] == round(sum(e["line_cost"] for e in result["shopping_list"]), 2)


def test_known_allergens_cover_seed_tags():
    for d in _dishes():
        assert set(d.allergens).issubset(KNOWN_ALLERGENS)
