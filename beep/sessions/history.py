"""Local conversation history storage."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from beep.sessions.history_support import SessionSummary
from beep.sessions.history_support import ensure_session_schema as _ensure_session_schema_impl
from beep.sessions.history_support import parse_timestamp as _parse_timestamp_impl
from beep.sessions.history_support import relative_time as _relative_time_impl
from beep.sessions.history_support import scan_session_file as _scan_session_file_impl
from beep.sessions.history_support import schema_entry as _schema_entry_impl
from beep.sessions.history_support import write_session_lines as _write_session_lines_impl

HISTORY_DIR = Path.home() / ".beepai" / "history"
SESSION_HISTORY_SCHEMA_VERSION = 1
_SESSION_HISTORY_SCHEMA_KIND = "session_history_schema"

# Auto-compaction: check every N appended messages
_COMPACTION_CHECK_INTERVAL = 10
# Estimated token budget before compaction is triggered (≈ 60k tokens)
_COMPACTION_TOKEN_THRESHOLD = 60_000

# Per-session append counter tracked in-process (not persisted)
_append_counter: dict[str, int] = {}


def _get_session_file(session_id: str) -> Path:
    """Get path to a session history file."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return HISTORY_DIR / f"{session_id}.jsonl"


def _schema_entry() -> dict[str, Any]:
    return _schema_entry_impl(
        schema_kind=_SESSION_HISTORY_SCHEMA_KIND,
        schema_version=SESSION_HISTORY_SCHEMA_VERSION,
    )


def _is_schema_entry(entry: dict[str, Any]) -> bool:
    return entry.get("role") == "meta" and entry.get("kind") == _SESSION_HISTORY_SCHEMA_KIND


def _write_session_lines(path: Path, lines: list[str]) -> None:
    _write_session_lines_impl(path, lines)


def _ensure_session_schema(path: Path, *, create_if_missing: bool = False) -> bool:
    return _ensure_session_schema_impl(
        path,
        schema_kind=_SESSION_HISTORY_SCHEMA_KIND,
        schema_version=SESSION_HISTORY_SCHEMA_VERSION,
        create_if_missing=create_if_missing,
    )


def _relative_time(dt: datetime | None) -> str:
    return _relative_time_impl(dt)


def _parse_timestamp(ts: str | None) -> datetime | None:
    return _parse_timestamp_impl(ts)


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate: 1 token ≈ 4 characters of content."""
    total_chars = sum(len(str(m.get("content") or "")) for m in messages)
    return total_chars // 4


def save_message(session_id: str, message: dict[str, Any]) -> None:
    """Append a message to session history, flushing immediately."""
    append_message(session_id, message)


def append_message(session_id: str, message: dict[str, Any]) -> None:
    """Append a single message to session history, flushing to disk immediately."""
    path = _get_session_file(session_id)
    if not _ensure_session_schema(path, create_if_missing=True):
        raise RuntimeError(f"Unsupported session history schema for {path}")
    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        **message,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()
        os.fsync(f.fileno())


def replace_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    """Atomically replace all messages in a session history file."""
    path = _get_session_file(session_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    lines = [json.dumps(_schema_entry())]
    for message in messages:
        entry = {
            "timestamp": now,
            "role": message.get("role", "user"),
            "content": message.get("content", ""),
        }
        lines.append(json.dumps(entry))
    _write_session_lines(path, lines)


def load_session(session_id: str) -> list[dict[str, Any]]:
    """Load all messages from a session."""
    path = _get_session_file(session_id)
    if not path.exists():
        return []
    if not _ensure_session_schema(path):
        return []

    messages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get("role") == "meta":
                        continue
                    messages.append({
                        "role": entry.get("role", "user"),
                        "content": entry.get("content", ""),
                    })
                except json.JSONDecodeError:
                    continue
    return messages


def list_sessions() -> list[SessionSummary]:
    """List all saved sessions as SessionSummary objects, newest first."""
    if not HISTORY_DIR.exists():
        return []

    summaries: list[SessionSummary] = []
    for path in sorted(HISTORY_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not _ensure_session_schema(path):
            continue
        scan = _scan_session_file_impl(path)
        if scan is None:
            continue

        summaries.append(
            SessionSummary(
                session_id=path.stem,
                created_at=_parse_timestamp(scan.first_timestamp),
                message_count=scan.message_count,
                last_message_preview=scan.last_message_preview,
            )
        )

    return summaries


def export_session(session_id: str, format: str = "md") -> str:
    """Export a session as Markdown or JSON string.

    Args:
        session_id: The session to export.
        format: ``"md"`` for Markdown, ``"json"`` for raw JSON array.

    Returns:
        The formatted string, or an empty string if the session does not exist.
    """
    messages = load_session(session_id)
    if not messages:
        return ""

    if format == "json":
        return json.dumps(messages, indent=2, ensure_ascii=False)

    # Markdown
    lines = [f"# Session {session_id}\n"]
    for msg in messages:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        lines.append(f"## {role}\n\n{content}\n")
    return "\n".join(lines)


def search_sessions(query: str) -> list[SessionSummary]:
    """Search all session JSONL files for messages containing *query* (case-insensitive).

    Returns a list of :class:`SessionSummary` for sessions that have at least
    one matching message, with ``last_message_preview`` set to the first
    matching snippet.
    """
    if not HISTORY_DIR.exists():
        return []

    query_lower = query.lower()
    results: list[SessionSummary] = []

    for path in sorted(HISTORY_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not _ensure_session_schema(path):
            continue
        scan = _scan_session_file_impl(path, query_lower=query_lower)
        if scan is None:
            continue

        if scan.match_preview:
            results.append(
                SessionSummary(
                    session_id=path.stem,
                    created_at=_parse_timestamp(scan.first_timestamp),
                    message_count=scan.message_count,
                    last_message_preview=scan.match_preview,
                )
            )

    return results


def maybe_compact_session(
    session_id: str,
    messages: list[dict[str, Any]],
    *,
    threshold: int = _COMPACTION_TOKEN_THRESHOLD,
) -> list[dict[str, Any]]:
    """Check token estimate and compact in-memory messages if over threshold.

    This is a *local* compaction only: keeps the system message plus the last
    20 messages.  Call :func:`replace_session` afterwards if you want to persist
    the result.

    Returns the (possibly compacted) messages list.
    """
    count = _append_counter.get(session_id, 0) + 1
    _append_counter[session_id] = count

    if count % _COMPACTION_CHECK_INTERVAL != 0:
        return messages

    if estimate_tokens(messages) < threshold:
        return messages

    system = messages[0]
    tail = messages[1:][-20:]
    return [system] + tail


def delete_session(session_id: str) -> bool:
    """Delete a session history file."""
    path = _get_session_file(session_id)
    if path.exists():
        path.unlink()
        return True
    return False


def create_session_id() -> str:
    """Generate a new session ID based on UTC timestamp + short UUID."""
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"{ts}-{short}"
