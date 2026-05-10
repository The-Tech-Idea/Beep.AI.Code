"""Tests for chat session commands."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from beep.chat.commands.session import ClearCommand, CompactCommand
from beep.sessions.history import load_session, save_message


@pytest.mark.asyncio
async def test_compact_prefers_server_result() -> None:
    cmd = CompactCommand()
    session = SimpleNamespace(
        _session_id="s-1",
        _messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ],
    )
    compacted = [{"role": "system", "content": "sys"}, {"role": "user", "content": "summary"}]
    client = SimpleNamespace(compact_conversation=AsyncMock(return_value={"messages": compacted}))
    await cmd.execute("", {"session": session, "client": client})
    assert session._messages == compacted


@pytest.mark.asyncio
async def test_clear_resets_session_and_coding_state() -> None:
    cmd = ClearCommand()
    state = {"watcher_stopped": False, "tasks_cancelled": False}

    class _Watcher:
        def stop(self) -> None:
            state["watcher_stopped"] = True

    class _TaskManager:
        def cancel_all(self) -> None:
            state["tasks_cancelled"] = True

    session = SimpleNamespace(
        _session_id="old-id",
        _messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ],
        _token_count=99,
        _request_count=5,
        _last_output="old output",
        _coding_project_id=42,
        _coding_session_id="s-42",
        _edit_target=Path("x.txt"),
        _last_edit={"path": "x.txt"},
        _task_manager=_TaskManager(),
        _watcher=_Watcher(),
    )

    def _clear_history() -> None:
        session._messages = [session._messages[0]]

    session.clear_history = _clear_history
    await cmd.execute("", {"session": session})

    assert session._session_id != "old-id"
    assert session._messages == [{"role": "system", "content": "sys"}]
    assert session._token_count == 0
    assert session._request_count == 0
    assert session._last_output == ""
    assert session._coding_project_id is None
    assert session._coding_session_id is None
    assert session._edit_target is None
    assert session._last_edit is None
    assert session._task_manager is None
    assert session._watcher is None
    assert state["watcher_stopped"] is True
    assert state["tasks_cancelled"] is True


@pytest.mark.asyncio
async def test_compact_falls_back_locally_on_error() -> None:
    cmd = CompactCommand()
    session = SimpleNamespace(
        _session_id="s-2",
        _messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "third"},
        ],
    )
    client = SimpleNamespace(
        compact_conversation=AsyncMock(side_effect=RuntimeError("missing endpoint")),
    )
    await cmd.execute("", {"session": session, "client": client})
    # With 3 non-system messages (≤ 5 limit), all messages are kept
    assert len(session._messages) == 4
    assert session._messages[0]["role"] == "system"
    assert session._messages[-1]["content"] == "third"


@pytest.mark.asyncio
async def test_compact_persists_rewritten_history(monkeypatch: pytest.MonkeyPatch) -> None:
    cmd = CompactCommand()
    with tempfile.TemporaryDirectory() as td:
        history_dir = Path(td) / "history"
        monkeypatch.setattr("beep.sessions.history.HISTORY_DIR", history_dir)
        session_id = "persist-compact"
        save_message(session_id, {"role": "system", "content": "sys"})
        save_message(session_id, {"role": "user", "content": "first"})
        save_message(session_id, {"role": "assistant", "content": "second"})
        save_message(session_id, {"role": "user", "content": "third"})
        session = SimpleNamespace(
            _session_id=session_id,
            _messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
                {"role": "user", "content": "third"},
            ],
        )
        client = SimpleNamespace(
            compact_conversation=AsyncMock(side_effect=RuntimeError("missing endpoint"))
        )
        await cmd.execute("", {"session": session, "client": client})
        loaded = load_session(session_id)
        # With 3 non-system messages (≤ 5 limit), all messages are kept
        assert len(loaded) == 4
        assert loaded[0]["role"] == "system"
        assert loaded[-1]["content"] == "third"
