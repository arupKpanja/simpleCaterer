"""Persistence for planning output (T1).

Stores each planning run as an Event with its option set, and reads it back.
Kept separate from the agents so the graph stays pure and the API layer owns
storage. Forward-compatible with tiered options (T2): ``save_event`` takes a
list of option dicts even though the MVP produces one.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.db.database import SessionLocal
from app.db.models import Event, Option, OptionMenuItem


def save_event(requirements: Dict, options: List[Dict]) -> str:
    """Persist an event + its options. Returns the new event id."""
    with SessionLocal() as session:
        event = Event(
            event_type=requirements.get("event_type", ""),
            guest_count=int(requirements.get("guest_count", 0) or 0),
            budget=float(requirements.get("budget", 0) or 0),
            dietary_restrictions=list(requirements.get("dietary_restrictions", []) or []),
            cuisine_pref=requirements.get("cuisine_pref", "") or "",
            location=requirements.get("location", "") or "",
            event_date=requirements.get("event_date", "") or "",
        )
        session.add(event)
        session.flush()  # assign event.id

        for opt in options:
            decor = opt.get("decor", {}) or {}
            venue = opt.get("venue", {}) or {}
            option = Option(
                event_id=event.id,
                tier=opt.get("tier", "standard"),
                theme=opt.get("theme", ""),
                food_cost=opt.get("food_cost", 0.0) or 0.0,
                decor_cost=opt.get("decor_cost", 0.0) or 0.0,
                venue_cost=opt.get("venue_cost", 0.0) or 0.0,
                total_cost=opt.get("total_cost", 0.0) or 0.0,
                per_guest=opt.get("per_guest", 0.0) or 0.0,
                within_budget=bool(opt.get("within_budget", True)),
                overage=opt.get("overage", 0.0) or 0.0,
                allergen_safe=bool(opt.get("allergen_safe", True)),
                decor_name=decor.get("name", "") or "",
                venue_name=venue.get("name", "") or "",
                shopping_list=opt.get("shopping_list", []) or [],
            )
            session.add(option)
            session.flush()
            opt["id"] = option.id  # backfill id so callers can reference/approve it
            for course in opt.get("courses", []):
                session.add(OptionMenuItem(
                    option_id=option.id,
                    course=course.get("course", ""),
                    dish_id=course.get("dish_id", 0),
                    dish_name=course.get("dish", ""),
                    cuisine=course.get("cuisine", ""),
                    diet_tags=course.get("diet_tags", []),
                    allergens=course.get("allergens", []),
                    serving_cost=course.get("serving_cost", 0.0) or 0.0,
                ))
        session.commit()
        return event.id


def _option_to_dict(option: Option) -> Dict:
    return {
        "id": option.id,
        "tier": option.tier,
        "theme": option.theme,
        "food_cost": option.food_cost,
        "decor_cost": option.decor_cost,
        "venue_cost": option.venue_cost,
        "total_cost": option.total_cost,
        "per_guest": option.per_guest,
        "within_budget": option.within_budget,
        "overage": option.overage,
        "allergen_safe": option.allergen_safe,
        "decor": {"name": option.decor_name, "cost": option.decor_cost},
        "venue": {"name": option.venue_name, "cost": option.venue_cost},
        "shopping_list": option.shopping_list,
        "courses": [
            {
                "course": mi.course,
                "dish_id": mi.dish_id,
                "dish": mi.dish_name,
                "cuisine": mi.cuisine,
                "diet_tags": mi.diet_tags,
                "allergens": mi.allergens,
                "serving_cost": mi.serving_cost,
            }
            for mi in option.menu_items
        ],
    }


def get_event(event_id: str) -> Optional[Dict]:
    """Fetch a stored event with its option set, or None if not found."""
    with SessionLocal() as session:
        event = session.get(Event, event_id)
        if event is None:
            return None
        return {
            "event_id": event.id,
            "requirements": {
                "event_type": event.event_type,
                "guest_count": event.guest_count,
                "budget": event.budget,
                "dietary_restrictions": event.dietary_restrictions,
                "cuisine_pref": event.cuisine_pref,
                "location": event.location,
                "event_date": event.event_date,
            },
            "created_at": event.created_at.isoformat(),
            "options": [_option_to_dict(o) for o in event.options],
        }
