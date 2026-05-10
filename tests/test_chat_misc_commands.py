"""Focused tests for chat misc command runtime behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from beep.chat.commands.misc import ClipboardCommand, ImageCommand, ImportCommand, SummaryCommand
from beep.chat.repl import ChatSession
from beep.sessions.history import load_session, save_message


@pytest.mark.asyncio
async def test_summary_command_forwards_coding_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock())
    session._messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "old"},
    ]
    session._coding_project_id = 12
    session._coding_session_id = "s-12"
    session._request_count = 0
    session._token_count = 0
    session._last_output = ""
    client = AsyncMock()
    client.chat_completion.return_value = {
        "choices": [{"message": {"content": "summary"}}],
        "usage": {"total_tokens": 9},
    }
    await SummaryCommand().execute("", {"session": session, "client": client})
    kwargs = client.chat_completion.await_args.kwargs
    assert kwargs["coding_assistant"]["project_id"] == 12
    assert kwargs["coding_assistant"]["session_id"] == "s-12"
    assert session._request_count == 1
    assert session._token_count == 9
    assert session._last_output == "summary"


@pytest.mark.asyncio
async def test_summary_command_handles_empty_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock())
    session._messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "old"},
    ]
    session._request_count = 0
    session._token_count = 0
    session._last_output = ""
    client = AsyncMock()
    client.chat_completion.return_value = {
        "choices": [{"message": {"content": "   "}}],
        "usage": {"total_tokens": 4},
    }
    await SummaryCommand().execute("", {"session": session, "client": client})
    out = capsys.readouterr().out
    assert "empty summary" in out.lower()
    assert session._request_count == 1
    assert session._token_count == 0
    assert session._last_output == ""


@pytest.mark.asyncio
async def test_summary_command_blocks_when_token_budget_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path.cwd())
    session = ChatSession(MagicMock())
    session._messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "old"},
    ]
    session._token_count = 18
    session._max_token_budget = 18
    client = AsyncMock()
    await SummaryCommand().execute("", {"session": session, "client": client})
    client.chat_completion.assert_not_awaited()
    assert session._request_count == 0
    assert session._last_output == ""


@pytest.mark.asyncio
async def test_clipboard_command_forwards_coding_metadata_and_usage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock())
    session._messages = [{"role": "system", "content": "sys"}]
    session._coding_project_id = 21
    session._coding_session_id = "s-21"
    session._token_count = 0
    session._last_output = ""
    client = MagicMock()
    client.chat_completion_stream.return_value = object()
    client.get_last_stream_usage.return_value = {"total_tokens": 5}
    monkeypatch.setattr("beep.utils.clipboard.get_clipboard", lambda: "clipboard text")
    monkeypatch.setattr("beep.chat.commands.misc.Confirm.ask", lambda _prompt: True)
    monkeypatch.setattr(
        "beep.chat.commands.llm_turns.render_stream",
        AsyncMock(return_value="clipboard response"),
    )
    await ClipboardCommand().execute("", {"session": session, "client": client})
    _, kwargs = client.chat_completion_stream.call_args
    assert kwargs["coding_assistant"]["project_id"] == 21
    assert kwargs["coding_assistant"]["session_id"] == "s-21"
    assert session._token_count == 5
    assert session._last_output == "clipboard response"


@pytest.mark.asyncio
async def test_image_command_forwards_coding_metadata_and_usage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    session = ChatSession(MagicMock())
    session._messages = [{"role": "system", "content": "sys"}]
    session._coding_project_id = 34
    session._coding_session_id = "s-34"
    session._token_count = 0
    session._last_output = ""
    client = MagicMock()
    client.chat_completion_stream.return_value = object()
    client.get_last_stream_usage.return_value = {"total_tokens": 10}
    monkeypatch.setattr(
        "beep.chat.commands.llm_turns.render_stream",
        AsyncMock(return_value="image response"),
    )
    await ImageCommand().execute(str(image_path), {"session": session, "client": client})
    _, kwargs = client.chat_completion_stream.call_args
    assert kwargs["coding_assistant"]["project_id"] == 34
    assert kwargs["coding_assistant"]["session_id"] == "s-34"
    assert session._token_count == 10
    assert session._last_output == "image response"


@pytest.mark.asyncio
async def test_import_command_persists_imported_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    monkeypatch.setattr("beep.sessions.history.HISTORY_DIR", tmp_path / "history")
    save_message("source-1", {"role": "user", "content": "src-u"})
    save_message("source-1", {"role": "assistant", "content": "src-a"})
    session = ChatSession(MagicMock())
    session._session_id = "target-1"
    session._messages = [{"role": "system", "content": "sys"}]
    session._token_count = 123
    session._last_output = "stale-output"
    await ImportCommand().execute("source-1", {"session": session})
    persisted = load_session("target-1")
    assert any(m["content"] == "src-u" for m in persisted)
    assert any(m["content"] == "src-a" for m in persisted)
    assert session._token_count == 0
    assert session._last_output == ""


@pytest.mark.asyncio
async def test_import_command_rejects_self_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock())
    session._session_id = "same-id"
    await ImportCommand().execute("same-id", {"session": session})
    out = capsys.readouterr().out
    assert "Cannot import current session into itself" in out
