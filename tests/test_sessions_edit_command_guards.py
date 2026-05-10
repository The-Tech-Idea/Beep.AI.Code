"""Tests for guardrails on sessions/edit commands."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from click.exceptions import Exit

from beep.commands.edit import edit_cmd
from beep.commands.sessions import (
    sessions_delete_cmd,
    sessions_export_cmd,
    sessions_list_cmd,
)
from beep.sessions.history import SessionSummary


def test_edit_cmd_handles_read_error(capsys) -> None:
    target = Path.cwd() / "AGENTS.md"
    with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
        with pytest.raises(Exit):
            edit_cmd(path=str(target), content="x", no_confirm=True)
    out = capsys.readouterr().out
    assert "error: denied" in out.lower()


def test_edit_cmd_handles_apply_error(capsys) -> None:
    target = Path.cwd() / "AGENTS.md"
    with patch("beep.commands.edit.apply_edit", side_effect=RuntimeError("boom")):
        with pytest.raises(Exit):
            edit_cmd(path=str(target), content="x", no_confirm=True)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_sessions_list_cmd_handles_list_error(capsys) -> None:
    with patch("beep.commands.sessions.list_sessions", side_effect=RuntimeError("boom")):
        with pytest.raises(Exit):
            sessions_list_cmd()
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_sessions_list_cmd_renders_session_summary(capsys) -> None:
    summaries = [
        SessionSummary(
            session_id="sess-123",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            message_count=3,
            last_message_preview="preview text",
        )
    ]
    with patch("beep.commands.sessions.list_sessions", return_value=summaries):
        sessions_list_cmd()
    out = capsys.readouterr().out
    assert "sess-123" in out
    assert "preview text" in out


def test_sessions_export_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.commands.sessions.export_markdown", side_effect=RuntimeError("boom")):
        with pytest.raises(Exit):
            sessions_export_cmd(session_id="abc", output=None, format="markdown")
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_sessions_export_cmd_rejects_invalid_format(capsys) -> None:
    with pytest.raises(Exit):
        sessions_export_cmd(session_id="abc", output=None, format="xml")
    out = capsys.readouterr().out
    assert "invalid format" in out.lower()


def test_sessions_delete_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.sessions.history.delete_session", side_effect=RuntimeError("boom")):
        with pytest.raises(Exit):
            sessions_delete_cmd(session_id="abc")
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()
