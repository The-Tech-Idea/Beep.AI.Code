"""Lightweight JSON logging controlled by environment flags."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any


def is_json_logging_enabled() -> bool:
    """Check whether JSON logging is enabled."""
    value = os.environ.get("BEEP_LOG_JSON", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def log_event(event: str, **fields: Any) -> None:
    """Emit a structured JSON log line when enabled."""
    if not is_json_logging_enabled():
        return
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=True))
