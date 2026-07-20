"""LangGraph wiring for the Part 1 planning graph.

Supervisor -> (fan out: one plan_tier worker per tier, in parallel) -> assemble.
The supervisor short-circuits to the end if the requirements are invalid.
``run_plan`` streams a stage event as each node finishes; ``plan`` returns the
final state in one shot (used by tests). Both return options sorted into tier
order (essential, standard, premium).
"""
from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Dict, Iterator, List, Optional

from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

from app.agents.checkpointer import get_checkpointer
from app.agents.state import EventState
from app.agents.supervisor import run_assemble, run_supervisor
from app.agents.tiers import TIERS, plan_tier

_TIER_RANK = {t: i for i, t in enumerate(TIERS)}


def _fan_out(state: EventState):
    """Dispatch one worker per tier, or end if the supervisor rejected the reqs."""
    if state.get("errors"):
        return END
    return [
        Send("plan_tier", {"requirements": state["requirements"],
                           "diet": state.get("diet", {}), "tier": tier})
        for tier in TIERS
    ]


@lru_cache(maxsize=1)
def get_graph():
    g = StateGraph(EventState)
    g.add_node("supervisor", run_supervisor)
    g.add_node("plan_tier", plan_tier)
    g.add_node("assemble", run_assemble)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", _fan_out, ["plan_tier", END])
    g.add_edge("plan_tier", "assemble")
    g.add_edge("assemble", END)
    # Checkpointed so each session's state is durable and resumable (T6).
    return g.compile(checkpointer=get_checkpointer())


def _initial_state(requirements: Dict) -> EventState:
    return {"requirements": requirements, "log": [], "errors": [], "options": []}


def _config(session_id: str) -> Dict:
    return {"configurable": {"thread_id": session_id}}


def _sorted_options(options: List[Dict]) -> List[Dict]:
    return sorted(options, key=lambda o: _TIER_RANK.get(o.get("tier"), 99))


def new_session_id() -> str:
    return uuid.uuid4().hex


def run_plan(requirements: Dict, session_id: Optional[str] = None) -> Iterator[Dict]:
    """Yield a stage event as each node completes, then a final result event.

    Every run is checkpointed under ``session_id`` (generated if not supplied),
    which is echoed back on the result event.
    """
    session_id = session_id or new_session_id()
    graph = get_graph()
    config = _config(session_id)
    state: Dict = _initial_state(requirements)

    for update in graph.stream(_initial_state(requirements), config=config,
                               stream_mode="updates"):
        for node, partial in update.items():
            if not partial:
                continue
            # merge (reducer channels: extend; scalars: replace)
            for key, value in partial.items():
                if key in ("options", "log", "errors"):
                    state[key] = [*state.get(key, []), *value]
                else:
                    state[key] = value
            for entry in partial.get("log", []):
                yield {"type": "stage", "node": node,
                       "stage": entry["stage"], "message": entry["message"]}

    yield {
        "type": "result",
        "session_id": session_id,
        "options": _sorted_options(state.get("options", [])),
        "errors": state.get("errors", []),
        "log": state.get("log", []),
    }


def plan(requirements: Dict, session_id: Optional[str] = None) -> EventState:
    """Run the graph to completion and return the final state (options tier-sorted)."""
    session_id = session_id or new_session_id()
    final = get_graph().invoke(_initial_state(requirements), config=_config(session_id))
    final["options"] = _sorted_options(final.get("options", []))
    final["session_id"] = session_id
    return final


def get_session_state(session_id: str) -> Optional[Dict]:
    """Return the checkpointed state for a session, or None if it has no checkpoint."""
    snapshot = get_graph().get_state(_config(session_id))
    values = snapshot.values if snapshot else None
    if not values:
        return None
    return {
        "session_id": session_id,
        "requirements": values.get("requirements", {}),
        "options": _sorted_options(values.get("options", [])),
        "errors": values.get("errors", []),
        "log": values.get("log", []),
    }
