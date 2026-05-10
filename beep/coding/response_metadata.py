"""Parse Coding Assistant metadata from model responses."""

from __future__ import annotations

import json
from typing import Any


def iter_json_objects(text: str) -> list[dict[str, Any]]:
    """Extract JSON objects embedded in arbitrary response text."""
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    index = 0
    while index < len(text):
        start = text.find("{", index)
        if start == -1:
            break
        try:
            value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(value, dict):
            objects.append(value)
        index = start + max(end, 1)
    return objects


def count_pending_approvals(text: str) -> int:
    """Count pending Coding Assistant approvals in embedded response metadata."""
    total = 0
    for payload in iter_json_objects(text):
        total += _count_pending_arrays(payload)
    return total


def find_coding_identity(text: str) -> tuple[int | None, str | None]:
    """Return project/session IDs from embedded Coding Assistant metadata."""
    for payload in iter_json_objects(text):
        identity = _find_identity(payload)
        if identity != (None, None):
            return identity
    return None, None


def _find_identity(value: Any) -> tuple[int | None, str | None]:
    if isinstance(value, dict):
        coding = value.get("coding_assistant")
        if isinstance(coding, dict):
            project_id = _coerce_project_id(coding.get("project_id"))
            session_id = _coerce_session_id(coding.get("session_id"))
            if project_id is not None or session_id is not None:
                return project_id, session_id

        project_id = _coerce_project_id(value.get("project_id"))
        session_id = _coerce_session_id(value.get("session_id"))
        if project_id is not None or session_id is not None:
            return project_id, session_id

        for child in value.values():
            identity = _find_identity(child)
            if identity != (None, None):
                return identity
    elif isinstance(value, list):
        for child in value:
            identity = _find_identity(child)
            if identity != (None, None):
                return identity
    return None, None


def _coerce_project_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _coerce_session_id(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _count_pending_arrays(value: Any) -> int:
    if isinstance(value, dict):
        total = 0
        for key, child in value.items():
            if key in {"pending_code_changes", "pending_approvals"} and isinstance(child, list):
                total += len(child)
            else:
                total += _count_pending_arrays(child)
        return total
    if isinstance(value, list):
        return sum(_count_pending_arrays(item) for item in value)
    return 0
