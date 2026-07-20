"""Typed shared state that flows through the LangGraph planning graph.

This is the ``EventState`` the plan refers to. Because the supervisor fans out
to one worker per tier that run in parallel, the channels those workers write —
``options``, ``log``, ``errors`` — use ``operator.add`` reducers so concurrent
appends merge instead of colliding. Single-writer fields (``requirements``,
``diet``) are written once by the supervisor before the fan-out.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, TypedDict


class Requirements(TypedDict, total=False):
    event_type: str
    guest_count: int
    budget: float
    dietary_restrictions: List[str]
    cuisine_pref: str
    location: str
    event_date: str


class EventState(TypedDict, total=False):
    requirements: Requirements
    # normalized diet constraints (written once by the supervisor)
    diet: Dict[str, Any]
    # per-invocation tier label passed to a worker via Send
    tier: str
    # costed options accumulated across the parallel tier workers
    options: Annotated[List[Dict[str, Any]], operator.add]
    # human-readable trace streamed to the UI
    log: Annotated[List[Dict[str, str]], operator.add]
    errors: Annotated[List[str], operator.add]


def log_entry(stage: str, message: str) -> List[Dict[str, str]]:
    """A single log entry, ready to merge into the add-reducer ``log`` channel."""
    return [{"stage": stage, "message": message}]
