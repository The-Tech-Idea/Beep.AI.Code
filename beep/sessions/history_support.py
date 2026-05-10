"""Support helpers for local conversation history storage."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SessionSummary:
    """Metadata about a saved session."""

    session_id: str
    created_at: datetime | None
    message_count: int
    last_message_preview: str


@dataclass
class SessionFileScan:
    """Derived metadata while scanning a session JSONL file."""

    first_timestamp: str | None
    message_count: int
    last_message_preview: str
    match_preview: str


def schema_entry(*, schema_kind: str, schema_version: int) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "role": "meta",
        "kind": schema_kind,
        "schema_version": schema_version,
    }


def is_schema_entry(entry: dict[str, Any], *, schema_kind: str) -> bool:
    return entry.get("role") == "meta" and entry.get("kind") == schema_kind


def write_session_lines(path: Path, lines: list[str]) -> None:
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line if line.endswith("\n") else f"{line}\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)


def ensure_session_schema(
    path: Path,
    *,
    schema_kind: str,
    schema_version: int,
    create_if_missing: bool = False,
) -> bool:
    if not path.exists():
        if create_if_missing:
            write_session_lines(path, [json.dumps(schema_entry(schema_kind=schema_kind, schema_version=schema_version))])
            return True
        return False

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False

    first_nonempty: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_nonempty = stripped
            break

    if first_nonempty is not None:
        try:
            first_entry = json.loads(first_nonempty)
        except json.JSONDecodeError:
            first_entry = None
        if isinstance(first_entry, dict) and is_schema_entry(first_entry, schema_kind=schema_kind):
            version = first_entry.get("schema_version")
            return isinstance(version, int) and version <= schema_version

    migrated_lines = [json.dumps(schema_entry(schema_kind=schema_kind, schema_version=schema_version)), *lines]
    write_session_lines(path, migrated_lines)
    return True


def relative_time(dt: datetime | None) -> str:
    """Return a human-readable relative time string (e.g. '3 hours ago')."""
    if dt is None:
        return "unknown"
    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = seconds // 86400
    return f"{days} day{'s' if days != 1 else ''} ago"


def parse_timestamp(ts: str | None) -> datetime | None:
    """Parse an ISO timestamp string to a UTC-aware datetime, or None."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def scan_session_file(path: Path, *, query_lower: str | None = None) -> SessionFileScan | None:
    """Scan a session JSONL file and collect summary or search metadata."""
    message_count = 0
    first_timestamp: str | None = None
    last_message_preview = ""
    match_preview = ""

    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if entry.get("role") == "meta":
                    continue

                message_count += 1
                if first_timestamp is None:
                    first_timestamp = entry.get("timestamp")

                content = str(entry.get("content") or "")
                last_message_preview = content[:80]
                if query_lower and not match_preview:
                    lowered = content.lower()
                    if query_lower in lowered:
                        index = lowered.find(query_lower)
                        start = max(0, index - 20)
                        match_preview = content[start : start + 80]
    except OSError:
        return None

    return SessionFileScan(
        first_timestamp=first_timestamp,
        message_count=message_count,
        last_message_preview=last_message_preview,
        match_preview=match_preview,
    )