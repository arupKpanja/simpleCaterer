"""Decor & Venue agent (T3).

Selects a decor package and a capacity-fitting venue for a given tier via the
MCP tool layer (no direct DB access), priced deterministically. Invoked once per
tier so decor/venue scale with the tier alongside the menu:

- decor packages are ranked by price → essential=cheapest, premium=priciest,
  standard=middle (same monotonic strategy as menu selection);
- venues are filtered to those that seat the guest count, then ranked by price
  and picked the same way. If none fit, the option carries no venue and flags it.

All costs are flat catalog prices (not per-guest). No LLM here — this is a
pricing/fit decision, so tools decide.
"""
from __future__ import annotations

from typing import Dict, Optional

from app.mcp import tools
from app.mcp.schemas import DecorDTO, VenueDTO


def _pick_by_tier(rows: list, tier: str):
    """Cheapest / middle / priciest for essential / standard / premium."""
    if not rows:
        return None
    if tier == "essential":
        return rows[0]
    if tier == "premium":
        return rows[-1]
    return rows[len(rows) // 2]


def select_decor_and_venue(tier: str, guest_count: int) -> Dict:
    """Return the chosen decor package + fitting venue for a tier, with costs."""
    decors = tools.get_decor_packages()  # priced ascending
    decor: Optional[DecorDTO] = _pick_by_tier(decors, tier)

    fitting = tools.get_venues(min_capacity=guest_count)  # priced ascending
    venue: Optional[VenueDTO] = _pick_by_tier(fitting, tier)

    note = "" if venue else f"No catalog venue seats {guest_count} guests — venue not included."
    return {
        "decor_name": decor.name if decor else "",
        "decor_style": decor.style if decor else "",
        "decor_cost": decor.price if decor else 0.0,
        "venue_name": venue.name if venue else "",
        "venue_capacity": venue.capacity if venue else 0,
        "venue_cost": venue.price if venue else 0.0,
        "venue_note": note,
    }
