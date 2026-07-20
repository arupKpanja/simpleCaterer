"""Supervisor agent + final assembly.

The supervisor validates requirements, normalizes the diet constraints once, and
fans out to one ``plan_tier`` worker per tier. ``run_assemble`` runs after all
workers converge and just summarizes the option set (the options themselves are
already accumulated in shared state).
"""
from __future__ import annotations

from typing import Dict, List

from app.agents.diet import parse_restrictions
from app.agents.state import EventState, log_entry


def run_supervisor(state: EventState) -> Dict:
    reqs = state.get("requirements", {})
    problems: List[str] = []
    if int(reqs.get("guest_count", 0) or 0) <= 0:
        problems.append("guest_count must be a positive number")
    if not reqs.get("event_type"):
        problems.append("event_type is required")

    if problems:
        return {
            "log": log_entry("supervisor",
                             "Cannot plan — invalid requirements: " + "; ".join(problems)),
            "errors": problems,
        }

    diet = parse_restrictions(reqs.get("dietary_restrictions", []))
    restrictions = reqs.get("dietary_restrictions", []) or []
    msg = (f"Planning a {reqs.get('event_type')} for {reqs.get('guest_count')} guests"
           + (f", budget {reqs.get('budget')}" if reqs.get("budget") else "")
           + (f", restrictions: {', '.join(restrictions)}" if restrictions else "")
           + ". Fanning out to essential / standard / premium tiers.")
    return {"diet": diet, "log": log_entry("supervisor", msg)}


def run_assemble(state: EventState) -> Dict:
    options = state.get("options", [])
    if not options:
        return {"log": log_entry("assemble", "No options were produced.")}
    return {
        "log": log_entry(
            "assemble",
            f"Assembled {len(options)} costed option(s): "
            + ", ".join(f"{o['tier']} ({o['total_cost']})" for o in options) + "."
        ),
    }
