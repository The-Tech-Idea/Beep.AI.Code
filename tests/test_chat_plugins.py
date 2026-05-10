"""Integration tests for chat plugin runtime wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from beep.chat.commands.misc import RetryCommand
from beep.chat.repl import ChatSession
from beep.config import BeepConfig


def _write_plugin(plugin_dir: Path) -> None:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.joinpath("chat_plugin.py").write_text(
        """
from beep.plugins.registry import CommandPlugin, ContextPlugin, PluginInfo

class EchoCommandPlugin(CommandPlugin):
    info = PluginInfo(name="echo-command")

    def activate(self): ...

    def get_commands(self):
        return {"echo": "Echo plugin response"}

    async def handle_command(self, command: str, args: str):
        return f"plugin-echo:{args}"

class PromptContextPlugin(ContextPlugin):
    info = PluginInfo(name="prompt-context")

    def activate(self): ...

    def get_context(self):
        return "Follow plugin context rules."
""",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_chat_session_uses_plugin_commands_and_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace_root = tmp_path
    _write_plugin(workspace_root / ".beep" / "plugins")
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace_root)

    session = ChatSession(MagicMock())
    assert "Follow plugin context rules." in session.messages[0]["content"]

    await session._handle_command("/echo hello")
    captured = capsys.readouterr()
    assert "plugin-echo:hello" in captured.out


def test_chat_session_skill_context_injection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root = tmp_path
    skill_dir = workspace_root / ".beep" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_dir.joinpath("security.md").write_text(
        """---
name: security
triggers: [security, auth]
priority: 7
---
Always validate auth scopes and sanitize inputs.
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace_root)

    session = ChatSession(MagicMock())
    context = session._build_skill_context("please review security auth flow")
    assert "Active Skills" in context
    assert "security" in context
    assert "sanitize inputs" in context


def test_chat_session_rules_context_injection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root = tmp_path
    workspace_root.joinpath("AGENTS.md").write_text(
        "Always keep auth boundaries strict.", encoding="utf-8"
    )
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace_root)

    session = ChatSession(MagicMock())
    assert len(session._rules) == 1
    from beep.rules.resolver import build_rules_context

    context = build_rules_context(session._rules)
    assert "Active Rules" in context
    assert "AGENTS.md" in context
    assert "Always keep auth boundaries strict." in session.messages[0]["content"]


def test_chat_session_includes_project_memory_in_system_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path
    workspace_root.joinpath(".beep.md").write_text(
        "Always prefer typed interfaces.",
        encoding="utf-8",
    )
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace_root)
    session = ChatSession(MagicMock())
    assert "Project Instructions" in session.messages[0]["content"]
    assert "Always prefer typed interfaces." in session.messages[0]["content"]


def test_resume_session_preserves_enriched_system_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path
    workspace_root.joinpath(".beep.md").write_text("Use concise answers.", encoding="utf-8")
    _write_plugin(workspace_root / ".beep" / "plugins")
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace_root)
    monkeypatch.setattr(
        "beep.sessions.history.load_session",
        lambda _sid: [{"role": "user", "content": "hello"}],
    )
    session = ChatSession(MagicMock())
    resumed = session.resume_session("s-1")
    assert resumed is True
    system_prompt = session.messages[0]["content"]
    assert "Project Instructions" in system_prompt
    assert "Use concise answers." in system_prompt
    assert "Plugin Context" in system_prompt


def test_resume_session_resets_usage_counters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(
        "beep.sessions.history.load_session",
        lambda _sid: [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "user", "content": "three"},
        ],
    )
    session = ChatSession(MagicMock())
    session._token_count = 999
    session._request_count = 999
    resumed = session.resume_session("s-usage")
    assert resumed is True
    assert session._token_count == 0
    assert session._request_count == 2


def test_resume_session_clears_stale_coding_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(
        "beep.sessions.history.load_session",
        lambda _sid: [{"role": "user", "content": "resumed"}],
    )
    session = ChatSession(MagicMock())
    session._coding_project_id = 99
    session._coding_session_id = "s-99"
    resumed = session.resume_session("s-new")
    assert resumed is True
    assert session._coding_project_id is None
    assert session._coding_session_id is None


def test_resume_session_clears_last_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(
        "beep.sessions.history.load_session",
        lambda _sid: [{"role": "user", "content": "resumed"}],
    )
    session = ChatSession(MagicMock())
    session._last_output = "stale output"
    resumed = session.resume_session("s-out")
    assert resumed is True
    assert session._last_output == ""


def test_update_coding_ids_from_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock())
    session._update_coding_ids('{"coding_assistant":{"project_id":42,"session_id":"s-42"}}')
    assert session.coding_project_id == 42
    assert session.coding_session_id == "s-42"


def test_chat_session_metadata_uses_configured_project_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock(), config=BeepConfig(project_id=88))
    assert session._get_coding_metadata() == {
        "workspace_root": str(tmp_path),
        "interaction_mode": "inline",
        "project_id": 88,
    }


@pytest.mark.asyncio
async def test_chat_session_bootstrap_uses_configured_project_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    client = MagicMock()
    client.bootstrap_project = AsyncMock(
        return_value={"success": True, "project_id": 88, "session_id": "s-88"}
    )
    client.bootstrap_workspace = AsyncMock()

    session = ChatSession(client, model="model-a", config=BeepConfig(project_id=88))
    await session._bootstrap_workspace()

    client.bootstrap_project.assert_awaited_once_with(
        88,
        interaction_mode="inline",
        model_id="model-a",
    )
    client.bootstrap_workspace.assert_not_called()
    assert session.coding_project_id == 88
    assert session.coding_session_id == "s-88"


def test_handle_coding_approvals_detects_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock())
    session._handle_coding_approvals('{"pending_code_changes":[{"id":1},{"id":2}]}')
    out = capsys.readouterr().out
    assert "Pending coding approvals detected" in out


@pytest.mark.asyncio
async def test_retry_command_forwards_coding_metadata_and_updates_usage(
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
    session._coding_project_id = 7
    session._coding_session_id = "s-7"
    session._token_count = 0
    session._last_output = ""
    client = MagicMock()
    client.chat_completion_stream.return_value = object()
    client.get_last_stream_usage.return_value = {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }
    cmd = RetryCommand()
    monkeypatch.setattr(
        "beep.chat.commands.llm_turns.render_stream", AsyncMock(return_value="new response")
    )
    await cmd.execute("", {"session": session, "client": client})
    _, kwargs = client.chat_completion_stream.call_args
    assert kwargs["coding_assistant"]["project_id"] == 7
    assert kwargs["coding_assistant"]["session_id"] == "s-7"
    assert session._messages[-1]["content"] == "new response"
    assert session._token_count == 15
    assert session._last_output == "new response"


@pytest.mark.asyncio
async def test_retry_command_keeps_user_turn_when_no_assistant_to_pop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: tmp_path)
    session = ChatSession(MagicMock())
    session._messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]
    client = MagicMock()
    client.chat_completion_stream.return_value = object()
    client.get_last_stream_usage.return_value = {"total_tokens": 1}
    cmd = RetryCommand()
    monkeypatch.setattr(
        "beep.chat.commands.llm_turns.render_stream", AsyncMock(return_value="retried")
    )
    await cmd.execute("", {"session": session, "client": client})
    user_messages = [m for m in session._messages if m.get("role") == "user"]
    assert len(user_messages) == 1
    assert user_messages[0]["content"] == "hello"
    assert session._messages[-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_retry_command_blocks_when_token_budget_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path.cwd())
    session = ChatSession(MagicMock())
    session._messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "old"},
    ]
    session._token_count = 25
    session._max_token_budget = 25
    client = MagicMock()
    cmd = RetryCommand()
    await cmd.execute("", {"session": session, "client": client})
    client.chat_completion_stream.assert_not_called()
    assert session._messages[-1]["content"] == "old"
