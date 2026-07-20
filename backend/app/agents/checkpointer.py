"""Checkpointer for the planning graph (T6).

Gives every planning run a durable, resumable state keyed by ``session_id``
(LangGraph ``thread_id``). Uses the file-backed SQLite saver so sessions survive
a process restart; falls back to the in-memory saver if that backend isn't
installed. This is also the mechanism the T5 approval-gate pause will resume on.
"""
from __future__ import annotations

import logging
import sqlite3
from functools import lru_cache

from app.config import settings

log = logging.getLogger("caterer.checkpointer")


@lru_cache(maxsize=1)
def get_checkpointer():
    """Return a singleton checkpointer (durable SQLite, else in-memory)."""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        conn = sqlite3.connect(
            settings.checkpoint_db_path,
            check_same_thread=False,  # FastAPI serves sync endpoints in a threadpool
        )
        saver = SqliteSaver(conn)
        setup = getattr(saver, "setup", None)
        if callable(setup):
            setup()
        log.info("Using durable SQLite checkpointer.")
        return saver
    except Exception as exc:  # noqa: BLE001
        from langgraph.checkpoint.memory import MemorySaver

        log.warning("SQLite checkpointer unavailable (%s); using in-memory saver.", exc)
        return MemorySaver()
