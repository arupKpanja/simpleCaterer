"""Quick end-to-end demo of the tiered Part 1 planning graph (deterministic path).

Run: python demo.py
"""
from app.agents.graph import run_plan

reqs = {
    "event_type": "wedding reception",
    "guest_count": 120,
    "budget": 60000,
    "dietary_restrictions": ["vegetarian", "no nuts"],
    "cuisine_pref": "Indian",
}

for ev in run_plan(reqs):
    if ev["type"] == "stage":
        print(f"[{ev['stage']}] {ev['message']}")
    else:
        print("\n=== COSTED OPTIONS ===")
        for o in ev["options"]:
            print(f"\n# {o['tier'].upper()} — {o['theme']} "
                  f"| total {o['total_cost']} ({o['per_guest']}/guest) "
                  f"| within_budget={o['within_budget']} | allergen_safe={o['allergen_safe']}")
            print(f"    food {o['food_cost']} + decor {o['decor_cost']} ({o['decor']['name']}) "
                  f"+ venue {o['venue_cost']} ({o['venue']['name'] or 'none'})")
            for c in o["courses"]:
                print(f"    {c['course']:8} {c['dish']:24} allergens={c['allergens']}")
