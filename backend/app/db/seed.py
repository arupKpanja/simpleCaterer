"""Seed the local catalog: priced inventory + a starter dish catalog.

Allergen tags live on the raw materials; a dish's allergens are *derived* from
its ingredients, so seeding correctly here is safety-critical (see risks in the
plan). Run ``python -m app.db.seed`` to (re)create and populate the DB.
"""
from __future__ import annotations

from app.db.database import Base, SessionLocal, engine
from app.db.models import (
    DecorPackage,
    Dish,
    DishIngredient,
    InventoryItem,
    Venue,
)

# --- Inventory: (name, unit, price_per_unit, stock_qty, allergens) ----------
INVENTORY = [
    ("Basmati rice", "kg", 120.0, 200.0, []),
    ("Paneer", "kg", 320.0, 40.0, ["dairy"]),
    ("Chicken", "kg", 240.0, 80.0, []),
    ("Prawns", "kg", 520.0, 20.0, ["shellfish"]),
    ("Potato", "kg", 30.0, 150.0, []),
    ("Onion", "kg", 40.0, 150.0, []),
    ("Tomato", "kg", 45.0, 120.0, []),
    ("Wheat flour", "kg", 45.0, 100.0, ["gluten"]),
    ("Semolina", "kg", 55.0, 40.0, ["gluten"]),
    ("Ghee", "kg", 600.0, 30.0, ["dairy"]),
    ("Cooking oil", "litre", 140.0, 60.0, []),
    ("Cashew", "kg", 900.0, 15.0, ["nuts"]),
    ("Milk", "litre", 60.0, 80.0, ["dairy"]),
    ("Yogurt", "kg", 90.0, 50.0, ["dairy"]),
    ("Sugar", "kg", 50.0, 80.0, []),
    ("Red lentils (dal)", "kg", 130.0, 60.0, []),
    ("Chickpeas", "kg", 110.0, 60.0, []),
    ("Mixed vegetables", "kg", 60.0, 100.0, []),
    ("Coconut", "kg", 80.0, 30.0, []),
    ("Spice mix", "kg", 400.0, 20.0, []),
    ("Salad greens", "kg", 90.0, 40.0, []),
    ("Seasonal fruit", "kg", 100.0, 50.0, []),
]

# --- Dishes: name -> (cuisine, course, diet_tags, {ingredient: qty_per_serving})
DISHES = {
    # starters
    "Veg Samosa": ("Indian", "starter", ["vegetarian"],
                   {"Wheat flour": 0.04, "Potato": 0.05, "Cooking oil": 0.02, "Spice mix": 0.005}),
    "Paneer Tikka": ("Indian", "starter", ["vegetarian", "gluten-free"],
                     {"Paneer": 0.06, "Yogurt": 0.02, "Spice mix": 0.005, "Onion": 0.02}),
    "Chicken Tikka": ("Indian", "starter", ["gluten-free"],
                      {"Chicken": 0.08, "Yogurt": 0.02, "Spice mix": 0.006}),
    "Prawn Koliwada": ("Indian", "starter", ["gluten-free"],
                       {"Prawns": 0.06, "Spice mix": 0.005, "Cooking oil": 0.02}),
    "Masala Papad": ("Indian", "starter", ["vegetarian", "vegan", "gluten-free"],
                     {"Chickpeas": 0.02, "Cooking oil": 0.008, "Onion": 0.02,
                      "Tomato": 0.02, "Spice mix": 0.003}),
    # mains
    "Chicken Biryani": ("Indian", "main", ["gluten-free"],
                        {"Chicken": 0.12, "Basmati rice": 0.12, "Onion": 0.04,
                         "Ghee": 0.02, "Spice mix": 0.01, "Yogurt": 0.02}),
    "Veg Biryani": ("Indian", "main", ["vegetarian", "vegan", "gluten-free"],
                    {"Basmati rice": 0.12, "Mixed vegetables": 0.1, "Onion": 0.04,
                     "Cooking oil": 0.02, "Spice mix": 0.01}),
    "Paneer Butter Masala": ("Indian", "main", ["vegetarian", "gluten-free"],
                             {"Paneer": 0.08, "Tomato": 0.06, "Cashew": 0.02,
                              "Ghee": 0.015, "Spice mix": 0.008}),
    "Dal Tadka": ("Indian", "main", ["vegetarian", "vegan", "gluten-free"],
                  {"Red lentils (dal)": 0.06, "Onion": 0.02, "Tomato": 0.02,
                   "Cooking oil": 0.01, "Spice mix": 0.006}),
    "Chana Masala": ("Indian", "main", ["vegetarian", "vegan", "gluten-free"],
                     {"Chickpeas": 0.07, "Onion": 0.03, "Tomato": 0.03,
                      "Cooking oil": 0.01, "Spice mix": 0.007}),
    # sides
    "Jeera Rice": ("Indian", "side", ["vegetarian", "vegan", "gluten-free"],
                   {"Basmati rice": 0.08, "Cooking oil": 0.01, "Spice mix": 0.003}),
    "Butter Naan": ("Indian", "side", ["vegetarian"],
                    {"Wheat flour": 0.08, "Milk": 0.02, "Ghee": 0.01}),
    "Vegetable Raita": ("Indian", "side", ["vegetarian", "gluten-free"],
                        {"Yogurt": 0.08, "Mixed vegetables": 0.02}),
    "Green Salad": ("Continental", "side", ["vegetarian", "vegan", "gluten-free"],
                    {"Salad greens": 0.06, "Tomato": 0.03, "Onion": 0.02}),
    # desserts
    "Gulab Jamun": ("Indian", "dessert", ["vegetarian"],
                    {"Milk": 0.05, "Wheat flour": 0.02, "Sugar": 0.04, "Ghee": 0.01}),
    "Gajar Halwa": ("Indian", "dessert", ["vegetarian", "gluten-free"],
                    {"Milk": 0.06, "Sugar": 0.04, "Cashew": 0.01, "Ghee": 0.01,
                     "Mixed vegetables": 0.05}),
    "Fruit Custard": ("Continental", "dessert", ["vegetarian", "gluten-free"],
                      {"Milk": 0.08, "Sugar": 0.03, "Mixed vegetables": 0.04}),
    "Coconut Ladoo": ("Indian", "dessert", ["vegetarian", "gluten-free"],
                      {"Coconut": 0.04, "Milk": 0.02, "Sugar": 0.03}),
    "Fresh Fruit Platter": ("Continental", "dessert", ["vegetarian", "vegan", "gluten-free"],
                            {"Seasonal fruit": 0.12, "Coconut": 0.01}),
}

# --- Decor packages: (name, style, price, description) ----------------------
DECOR = [
    ("Simple Elegance", "minimal", 8000.0, "Table linens, centrepieces, basic lighting."),
    ("Classic Celebration", "classic", 18000.0, "Floral arch, stage backdrop, ambient lighting."),
    ("Grand Affair", "luxury", 40000.0, "Full floral, themed stage, uplighting, drapery, props."),
]

# --- Venues: (name, style, capacity, price) ---------------------------------
VENUES = [
    ("Community Hall", "indoor", 150, 15000.0),
    ("Garden Lawn", "outdoor", 300, 35000.0),
    ("Banquet Ballroom", "indoor", 500, 70000.0),
    ("Riverside Marquee", "outdoor", 250, 50000.0),
]


def seed(reset: bool = True) -> None:
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        if session.query(InventoryItem).count() > 0 and not reset:
            return  # already seeded

        items = {}
        for name, unit, price, stock, allergens in INVENTORY:
            item = InventoryItem(
                name=name, unit=unit, price_per_unit=price,
                stock_qty=stock, allergens=list(allergens),
            )
            session.add(item)
            items[name] = item
        session.flush()

        for name, (cuisine, course, diet_tags, recipe) in DISHES.items():
            dish = Dish(name=name, cuisine=cuisine, course=course, diet_tags=list(diet_tags))
            session.add(dish)
            session.flush()
            for ing_name, qty in recipe.items():
                if ing_name not in items:
                    raise ValueError(f"Dish {name!r} references unknown item {ing_name!r}")
                session.add(DishIngredient(dish_id=dish.id, item_id=items[ing_name].id,
                                           qty_per_serving=qty))

        for name, style, price, desc in DECOR:
            session.add(DecorPackage(name=name, style=style, price=price, description=desc))
        for name, style, capacity, price in VENUES:
            session.add(Venue(name=name, style=style, capacity=capacity, price=price))
        session.commit()

    print(f"Seeded {len(INVENTORY)} inventory items, {len(DISHES)} dishes, "
          f"{len(DECOR)} decor packages, {len(VENUES)} venues.")


if __name__ == "__main__":
    seed()
