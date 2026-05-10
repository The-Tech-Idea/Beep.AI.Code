"""Session export functionality."""

from __future__ import annotations

from pathlib import Path

from beep.sessions.history import export_session


def _get_export_content(session_id: str, *, format: str) -> str:
    content = export_session(session_id, format=format)
    if not content:
        raise ValueError(f"No messages found for session: {session_id}")
    return content


def export_markdown(session_id: str, output_path: Path | None = None) -> Path:
    """Export a session as markdown."""
    content = _get_export_content(session_id, format="md")
    output = output_path or Path(f"session-{session_id}.md")
    output.write_text(content, encoding="utf-8")
    return output


def export_json(session_id: str, output_path: Path | None = None) -> Path:
    """Export a session as JSON."""
    content = _get_export_content(session_id, format="json")
    output = output_path or Path(f"session-{session_id}.json")
    output.write_text(content, encoding="utf-8")
    return output
