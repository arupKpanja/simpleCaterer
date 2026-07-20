"""Structured logging setup (T10).

One place to configure logging for the app. Human-readable console format by
default; set ``CATERER_LOG_JSON=true`` for single-line JSON logs suitable for
aggregation. Level via ``CATERER_LOG_LEVEL``.
"""
from __future__ import annotations

import json
import logging
import sys

from app.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str | None = None, as_json: bool | None = None) -> None:
    """Install a single stdout handler on the root logger (idempotent)."""
    level = (level or settings.log_level).upper()
    as_json = settings.log_json if as_json is None else as_json

    handler = logging.StreamHandler(sys.stdout)
    if as_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # keep uvicorn's access/error logs flowing through our handler
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
