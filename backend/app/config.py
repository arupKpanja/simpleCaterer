"""Application settings.

Everything runs locally. Configuration is read from environment variables
(prefixed ``CATERER_``) with sensible local-first defaults, so the system runs
with zero setup and no external services.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (two parents up from app/config.py)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CATERER_", env_file=".env", extra="ignore")

    # --- Database -------------------------------------------------------
    # SQLite by default (single file, zero setup). Swap to a Postgres URL to
    # move to the production-faithful DB without code changes.
    database_url: str = f"sqlite:///{(BASE_DIR / 'caterer.db').as_posix()}"

    # --- LLM inference --------------------------------------------------
    # When Ollama is reachable at this URL the real model is used; otherwise
    # the deterministic rule-based fallback kicks in automatically.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    # Force the deterministic planner even if Ollama is up (useful for tests).
    force_fallback_llm: bool = False
    llm_timeout_seconds: float = 60.0

    # --- Planning defaults ---------------------------------------------
    default_courses: int = 4  # starter, main, side, dessert

    # --- Logging --------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False  # set true for structured JSON logs (prod/aggregation)

    # --- Checkpointer ---------------------------------------------------
    # LangGraph checkpoint store (SQLite file). Point at a mounted volume in
    # Docker so session state survives container restarts.
    checkpoint_db_path: str = str(BASE_DIR / "checkpoints.db")


settings = Settings()
