"""T6: session checkpointing — state is durable and resumable by session_id."""
from app.agents.graph import (
    get_checkpointer,
    get_graph,
    get_session_state,
    new_session_id,
    plan,
    run_plan,
)


def _reqs(**over):
    base = {"event_type": "reception", "guest_count": 120, "budget": 200000,
            "dietary_restrictions": [], "cuisine_pref": "Indian"}
    base.update(over)
    return base


def test_plan_echoes_session_id():
    sid = new_session_id()
    state = plan(_reqs(), session_id=sid)
    assert state["session_id"] == sid


def test_session_state_retrievable():
    sid = new_session_id()
    planned = plan(_reqs(), session_id=sid)
    state = get_session_state(sid)
    assert state is not None
    assert state["session_id"] == sid
    assert [o["tier"] for o in state["options"]] == [o["tier"] for o in planned["options"]]


def test_unknown_session_returns_none():
    assert get_session_state("never-planned") is None


def test_state_survives_checkpointer_reload():
    """Clearing the cached graph/checkpointer simulates a restart; SQLite persists."""
    sid = new_session_id()
    plan(_reqs(), session_id=sid)

    # drop the in-process singletons and rebuild from the on-disk checkpoint file
    get_graph.cache_clear()
    get_checkpointer.cache_clear()

    reloaded = get_session_state(sid)
    assert reloaded is not None
    assert len(reloaded["options"]) == 3


def test_stream_result_carries_session_id():
    sid = new_session_id()
    result = list(run_plan(_reqs(), session_id=sid))[-1]
    assert result["type"] == "result"
    assert result["session_id"] == sid
