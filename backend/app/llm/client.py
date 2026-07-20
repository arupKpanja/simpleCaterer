"""LLM client abstraction.

Uses a local **Ollama** model when one is reachable; otherwise reports itself
unavailable so callers take the deterministic rule-based path. This keeps the
whole system runnable and testable before Ollama is installed, and preserves
the "model proposes, tools decide" principle — the LLM only ever *suggests*;
constraint and cost enforcement is deterministic downstream.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.config import settings

log = logging.getLogger("caterer.llm")


class LLMClient:
    def __init__(self) -> None:
        self._available: Optional[bool] = None  # cached health result

    def is_available(self) -> bool:
        """True when a real model can be reached. Cached after first check."""
        if settings.force_fallback_llm:
            return False
        if self._available is not None:
            return self._available
        try:
            resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
            self._available = resp.status_code == 200
        except Exception as exc:  # noqa: BLE001 - any failure => fall back
            log.info("Ollama not reachable (%s); using deterministic fallback.", exc)
            self._available = False
        return self._available

    def complete(self, prompt: str, system: Optional[str] = None,
                 json_mode: bool = False) -> str:
        """Run a single completion against Ollama. Raises if unavailable."""
        if not self.is_available():
            raise RuntimeError("LLM unavailable; caller should use the fallback path.")
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
            timeout=settings.llm_timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def complete_json(self, prompt: str, system: Optional[str] = None) -> Optional[dict]:
        """Completion parsed as JSON; returns None on any failure (caller falls back)."""
        try:
            raw = self.complete(prompt, system=system, json_mode=True)
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM JSON completion failed (%s); falling back.", exc)
            return None


# module-level singleton
llm = LLMClient()
