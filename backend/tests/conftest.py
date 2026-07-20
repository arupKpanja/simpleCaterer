"""Test fixtures: an isolated seeded SQLite DB and forced LLM fallback.

Sets env before app modules import so the DB points at a throwaway file and the
deterministic planner is used (no Ollama needed in CI).
"""
import os
import tempfile

import pytest

_TMP_DB = os.path.join(tempfile.gettempdir(), "caterer_test.db")
os.environ["CATERER_DATABASE_URL"] = f"sqlite:///{_TMP_DB.replace(os.sep, '/')}"
os.environ["CATERER_FORCE_FALLBACK_LLM"] = "true"


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    if os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)
    from app.db.seed import seed
    seed(reset=True)
    yield
    if os.path.exists(_TMP_DB):
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass
