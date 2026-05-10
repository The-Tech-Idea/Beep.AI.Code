"""Tests for AI-assisted quality/workflow commands."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from beep.chat.commands.quality import ReviewCommand
from beep.chat.commands.workflow import BashCommand, CommitCommand, OutputCommand, PRCommand


@pytest.mark.asyncio
async def test_review_command_forwards_coding_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.commands.quality.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.quality.get_git_diff", lambda _root: "diff --git a b")
    monkeypatch.setattr(
        "beep.chat.commands.llm_turns.render_stream", AsyncMock(return_value="review output")
    )
    session = SimpleNamespace(
        _messages=[{"role": "system", "content": "sys"}],
        _model=None,
        _session_id="s-review",
        _coding_project_id=11,
        _coding_session_id="cs-11",
        _request_count=0,
        _token_count=0,
        _last_output="",
        _show_tokens=False,
        _save=lambda _role, _content: None,
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 11,
            "session_id": "cs-11",
            "interaction_mode": "inline",
        },
    )
    client = MagicMock()
    client.chat_completion_stream.return_value = object()
    client.get_last_stream_usage.return_value = {"total_tokens": 6}
    cmd = ReviewCommand()
    await cmd.execute("", {"session": session, "client": client})
    _, kwargs = client.chat_completion_stream.call_args
    assert kwargs["coding_assistant"]["project_id"] == 11
    assert kwargs["coding_assistant"]["session_id"] == "cs-11"
    assert session._request_count == 1
    assert session._token_count > 0
    session._handle_coding_approvals.assert_called_once_with("review output")
    assert "review output" in session._last_output


@pytest.mark.asyncio
async def test_review_command_handles_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.commands.quality.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.quality.get_git_diff", lambda _root: "diff --git a b")
    monkeypatch.setattr("beep.chat.commands.llm_turns.render_stream", AsyncMock(return_value="   "))
    session = SimpleNamespace(
        _messages=[{"role": "system", "content": "sys"}],
        _model=None,
        _session_id="s-review-empty",
        _coding_project_id=11,
        _coding_session_id="cs-11",
        _request_count=0,
        _token_count=0,
        _last_output="",
        _show_tokens=False,
        _save=lambda _role, _content: None,
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 11,
            "session_id": "cs-11",
            "interaction_mode": "inline",
        },
    )
    client = MagicMock()
    client.chat_completion_stream.return_value = object()
    cmd = ReviewCommand()
    await cmd.execute("", {"session": session, "client": client})
    out = capsys.readouterr().out
    assert "empty review" in out.lower()
    assert session._token_count == 0
    assert session._last_output == ""


@pytest.mark.asyncio
async def test_review_command_blocks_when_token_budget_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.commands.quality.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.quality.get_git_diff", lambda _root: "diff --git a b")
    session = SimpleNamespace(
        _messages=[{"role": "system", "content": "sys"}],
        _model=None,
        _session_id="s-review-budget",
        _coding_project_id=11,
        _coding_session_id="cs-11",
        _request_count=0,
        _token_count=30,
        _max_token_budget=30,
        _last_output="",
        _show_tokens=False,
        _save=lambda _role, _content: None,
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 11,
            "session_id": "cs-11",
            "interaction_mode": "inline",
        },
    )
    client = MagicMock()
    cmd = ReviewCommand()
    await cmd.execute("", {"session": session, "client": client})
    client.chat_completion_stream.assert_not_called()
    assert session._request_count == 0


@pytest.mark.asyncio
async def test_commit_command_forwards_coding_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.commands.workflow.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.workflow.get_git_diff", lambda _root: "diff --git a b")
    monkeypatch.setattr("beep.chat.commands.workflow.Confirm.ask", lambda _prompt: False)
    session = SimpleNamespace(
        _session_id="s-commit",
        _request_count=0,
        _token_count=0,
        _last_output="",
        _coding_project_id=22,
        _coding_session_id="cs-22",
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 22,
            "session_id": "cs-22",
            "interaction_mode": "inline",
        },
    )
    client = AsyncMock()
    client.chat_completion.return_value = {"choices": [{"message": {"content": "feat: add x"}}]}
    cmd = CommitCommand()
    await cmd.execute("", {"session": session, "client": client})
    kwargs = client.chat_completion.await_args.kwargs
    assert kwargs["coding_assistant"]["project_id"] == 22
    assert kwargs["coding_assistant"]["session_id"] == "cs-22"
    assert session._request_count == 1
    assert session._token_count > 0
    assert "feat: add x" in session._last_output
    session._handle_coding_approvals.assert_called_once_with("feat: add x")


@pytest.mark.asyncio
async def test_pr_command_forwards_coding_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.commands.workflow.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.workflow.get_git_diff", lambda _root: "diff --git a b")
    session = SimpleNamespace(
        _session_id="s-pr",
        _request_count=0,
        _token_count=0,
        _last_output="",
        _coding_project_id=33,
        _coding_session_id="cs-33",
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 33,
            "session_id": "cs-33",
            "interaction_mode": "inline",
        },
    )
    client = AsyncMock()
    client.chat_completion.return_value = {
        "choices": [{"message": {"content": "PR title\n\nbody"}}]
    }
    cmd = PRCommand()
    await cmd.execute("", {"session": session, "client": client})
    kwargs = client.chat_completion.await_args.kwargs
    assert kwargs["coding_assistant"]["project_id"] == 33
    assert kwargs["coding_assistant"]["session_id"] == "cs-33"
    assert session._request_count == 1
    assert session._token_count > 0
    assert "PR title" in session._last_output
    session._handle_coding_approvals.assert_called_once_with("PR title\n\nbody")


@pytest.mark.asyncio
async def test_commit_command_handles_empty_model_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.commands.workflow.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.workflow.get_git_diff", lambda _root: "diff --git a b")
    session = SimpleNamespace(
        _session_id="s-commit-empty",
        _request_count=0,
        _token_count=0,
        _last_output="",
        _coding_project_id=22,
        _coding_session_id="cs-22",
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 22,
            "session_id": "cs-22",
            "interaction_mode": "inline",
        },
    )
    client = AsyncMock()
    client.chat_completion.return_value = {"choices": [{"message": {"content": "   "}}]}
    cmd = CommitCommand()
    await cmd.execute("", {"session": session, "client": client})
    out = capsys.readouterr().out
    assert "empty commit message" in out.lower()
    assert session._last_output == ""


@pytest.mark.asyncio
async def test_commit_command_blocks_when_token_budget_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.commands.workflow.find_workspace_root", lambda: Path.cwd())
    session = SimpleNamespace(
        _session_id="s-commit-budget",
        _request_count=0,
        _token_count=120,
        _max_token_budget=120,
        _last_output="",
        _coding_project_id=22,
        _coding_session_id="cs-22",
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 22,
            "session_id": "cs-22",
            "interaction_mode": "inline",
        },
    )
    client = AsyncMock()
    cmd = CommitCommand()
    await cmd.execute("", {"session": session, "client": client})
    client.chat_completion.assert_not_awaited()
    assert session._request_count == 0


@pytest.mark.asyncio
async def test_pr_command_handles_empty_model_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.commands.workflow.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.workflow.get_git_diff", lambda _root: "diff --git a b")
    session = SimpleNamespace(
        _session_id="s-pr-empty",
        _request_count=0,
        _token_count=0,
        _last_output="",
        _coding_project_id=33,
        _coding_session_id="cs-33",
        _update_coding_ids=MagicMock(),
        _handle_coding_approvals=MagicMock(),
        _get_coding_metadata=lambda: {
            "project_id": 33,
            "session_id": "cs-33",
            "interaction_mode": "inline",
        },
    )
    client = AsyncMock()
    client.chat_completion.return_value = {"choices": [{"message": {"content": ""}}]}
    cmd = PRCommand()
    await cmd.execute("", {"session": session, "client": client})
    out = capsys.readouterr().out
    assert "empty pr description" in out.lower()
    assert session._last_output == ""


@pytest.mark.asyncio
async def test_bash_command_persists_output_for_output_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _Proc:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"hello\n", b""

    async def _spawn(*_args: object, **_kwargs: object) -> _Proc:
        return _Proc()

    monkeypatch.setattr("beep.chat.commands.workflow.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr("beep.chat.commands.workflow.asyncio.create_subprocess_shell", _spawn)
    session = SimpleNamespace(_last_output="")
    bash = BashCommand()
    output = OutputCommand()
    await bash.execute("echo hello", {"session": session})
    assert "hello" in session._last_output
    await output.execute("", {"session": session})
    out = capsys.readouterr().out
    assert "hello" in out
