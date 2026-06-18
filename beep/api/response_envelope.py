"""Normalize Beep.AI.Server V1 JSON envelopes for API clients."""

from __future__ import annotations

from typing import Any


def unwrap_v1_envelope(body: dict[str, Any]) -> dict[str, Any]:
    """Return the inner payload from canonical ``{status, data}`` responses."""
    if not isinstance(body, dict):
        return {}
    if body.get("status") == "success" and isinstance(body.get("data"), dict):
        return body["data"]
    return body
