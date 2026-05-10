"""Chat command dispatch and send behavior tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from rich.console import Console

from beep.chat.commands.base import Command
from beep.chat.commands.coding import CodingCommand
from beep.chat.commands.misc import ClipboardCommand
from beep.chat.repl import ChatSession
from beep.chat import repl_runtime_support
from beep.config import BeepConfig
from beep.workspace.editing import PreparedWorkspaceEdit


def _write_mcp_definition(workspace: Path, *, name: str = "demo") -> None:
    server_path = workspace / ".beep" / "mcp" / f"{name}.json"
    server_path.parent.mkdir(parents=True, exist_ok=True)
    server_path.write_text(
        (
            "{\n"
            f'  "name": "{name}",\n'
            '  "command": "npx",\n'
            '  "args": ["-y", "demo-mcp"],\n'
            '  "tools": [\n'
            "    {\n"
            '      "name": "demo_tool",\n'
            '      "description": "Demo MCP tool",\n'
            '      "parameters": {}\n'
            "    }\n"
            "  ]\n"
            "}\n"
        ),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_coding_command_off_clears_linkage_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())
    session._coding_project_id = 501
    session._coding_session_id = "s-501"
    cmd = CodingCommand()
    await cmd.execute("off", {"session": session})
    assert session.coding_enabled is False
    assert session._coding_project_id is None
    assert session._coding_session_id is None


@pytest.mark.asyncio
async def test_coding_command_on_enables_coding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())
    session.set_coding_enabled(False)
    cmd = CodingCommand()
    await cmd.execute("on", {"session": session})
    assert session.coding_enabled is True


@pytest.mark.asyncio
async def test_handle_command_logs_error_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BoomCommand(Command):
        @property
        def name(self) -> str:
            return "boom"

        @property
        def description(self) -> str:
            return "boom"

        async def execute(self, args: str, ctx: dict[str, object]) -> None:
            raise RuntimeError("boom")

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())
    session._commands["boom"] = BoomCommand()
    log_mock = MagicMock()
    monkeypatch.setattr("beep.chat.repl.log_event", log_mock)
    await session._handle_command("/boom")
    assert any(
        call.args and call.args[0] == "chat.command.error" for call in log_mock.call_args_list
    )


@pytest.mark.asyncio
async def test_handle_command_logs_unknown_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())
    log_mock = MagicMock()
    monkeypatch.setattr("beep.chat.repl.log_event", log_mock)
    await session._handle_command("/does-not-exist")
    assert any(
        call.args and call.args[0] == "chat.command.unknown" for call in log_mock.call_args_list
    )


@pytest.mark.asyncio
async def test_handle_command_logs_plugin_error_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())
    log_mock = MagicMock()
    monkeypatch.setattr("beep.chat.repl.log_event", log_mock)
    session._plugin_runtime.registry.handle_plugin_command = AsyncMock(
        side_effect=RuntimeError("plugin boom")
    )
    await session._handle_command("/plugin-fail")
    assert any(
        call.args and call.args[0] == "chat.command.plugin.error"
        for call in log_mock.call_args_list
    )


@pytest.mark.asyncio
async def test_clipboard_copy_uses_last_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())
    session._last_output = "latest answer"
    copied: dict[str, str] = {}
    monkeypatch.setattr("beep.utils.clipboard.get_clipboard", lambda: "ignored")
    monkeypatch.setattr(
        "beep.utils.clipboard.set_clipboard",
        lambda value: copied.setdefault("value", value),
    )
    cmd = ClipboardCommand()
    await cmd.execute("--copy", {"session": session})
    assert copied["value"] == "latest answer"
    assert "Copied last response" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_clipboard_copy_warns_when_no_last_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())
    session._last_output = ""
    monkeypatch.setattr("beep.utils.clipboard.get_clipboard", lambda: "ignored")
    cmd = ClipboardCommand()
    await cmd.execute("--copy", {"session": session})
    assert "No recent response to copy" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_send_blocks_when_max_token_budget_reached(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path.cwd())
    session = ChatSession(MagicMock())
    session._max_token_budget = 10
    session._token_count = 10
    client = MagicMock()
    session._client = client
    await session.send("hello")
    out = capsys.readouterr().out
    assert "Token budget reached" in out
    assert len(session._messages) == 1
    assert client.chat_completion_stream.call_count == 0


@pytest.mark.asyncio
async def test_send_updates_last_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr(
        "beep.chat.commands.llm_turns.render_stream",
        AsyncMock(return_value="assistant reply"),
    )
    session = ChatSession(MagicMock())
    session._client = MagicMock()
    session._client.chat_completion_stream.return_value = object()
    session._client.get_last_stream_usage.return_value = {"total_tokens": 7}
    await session.send("hello")
    assert session._last_output == "assistant reply"


@pytest.mark.asyncio
async def test_send_handles_empty_model_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path.cwd())
    monkeypatch.setattr(
        "beep.chat.commands.llm_turns.render_stream",
        AsyncMock(return_value="   "),
    )
    session = ChatSession(MagicMock())
    session._client = MagicMock()
    session._client.chat_completion_stream.return_value = object()
    session._last_output = "previous"
    await session.send("hello")
    out = capsys.readouterr().out
    assert "empty response" in out.lower()
    assert len(session._messages) == 2
    assert session._messages[-1]["role"] == "user"
    assert session._last_output == "previous"


@pytest.mark.asyncio
async def test_run_uses_shared_workspace_edit_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    session._edit_target = Path("notes.txt")
    session._last_edit = None
    session._commands = {}
    session._bootstrap_workspace = AsyncMock()
    session._show_welcome = MagicMock()

    prepared = PreparedWorkspaceEdit(
        path=Path("notes.txt"),
        old_content="before",
        new_content="after",
    )
    apply_mock = MagicMock()

    monkeypatch.setattr(
        "beep.chat.repl_runtime_support.Prompt.ask",
        MagicMock(side_effect=["after", ""]),
    )
    monkeypatch.setattr(
        "beep.chat.repl_runtime_support.prepare_workspace_edit",
        MagicMock(return_value=prepared),
    )
    monkeypatch.setattr("beep.chat.repl_runtime_support.apply_edit", apply_mock)

    await repl_runtime_support.run(
        session,
        console=Console(record=True),
        read_multiline=MagicMock(return_value=None),
    )

    assert session._last_edit == {
        "path": Path("notes.txt"),
        "old": "before",
        "new": "after",
    }
    assert session._edit_target is None
    apply_mock.assert_called_once_with(
        Path("notes.txt"),
        "before",
        "after",
        require_confirm=True,
    )


@pytest.mark.asyncio
async def test_handle_command_persists_task_manager_across_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instances: list[object] = []

    class _TaskManager:
        def __init__(self) -> None:
            self.tasks: list[object] = []
            instances.append(self)

        async def start(self, name: str, command: str, cwd: str | None = None) -> object:
            task = SimpleNamespace(
                id="task-1",
                name=name,
                command=command,
                status=SimpleNamespace(value="running"),
                output="",
                error="",
            )
            self.tasks.append(task)
            return task

        def get(self, task_id: str) -> object | None:
            for task in self.tasks:
                if task.id == task_id:
                    return task
            return None

        def list_all(self) -> list[object]:
            return list(self.tasks)

        async def cancel(self, task_id: str) -> bool:
            return self.get(task_id) is not None

        def cancel_all(self) -> None:
            return None

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        monkeypatch.setattr("beep.tasks.manager.TaskManager", _TaskManager)
        monkeypatch.setattr("beep.app_service.TaskManager", _TaskManager)
        session = ChatSession(MagicMock())

    await session._handle_command("/task run build pytest")
    await session._handle_command("/task")

    out = capsys.readouterr().out
    assert len(instances) == 1
    assert session._task_manager is instances[0]
    assert "build" in out
    assert "pytest" in out


@pytest.mark.asyncio
async def test_handle_command_persists_watcher_across_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instances: list[object] = []

    class _WatcherService:
        def __init__(self, *_args, **_kwargs) -> None:
            self.rules: list[object] = []
            self._running = False
            instances.append(self)

        def add_rule(self, pattern: str, command: str) -> str:
            self.rules.append(SimpleNamespace(pattern=pattern, command=command, enabled=True))
            return f"{pattern} -> {command}"

        def remove_rule(self, index: int) -> bool:
            return False

        def list_rules(self) -> list[tuple[int, object]]:
            return list(enumerate(self.rules))

        def start(self, callback) -> None:
            self._running = True

        def stop(self) -> None:
            self._running = False

        @property
        def is_running(self) -> bool:
            return self._running

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        monkeypatch.setattr("beep.watcher.service.WatcherService", _WatcherService)
        monkeypatch.setattr("beep.app_service.WatcherService", _WatcherService)
        session = ChatSession(MagicMock())

    await session._handle_command("/watch add *.py pytest")
    await session._handle_command("/watch")

    out = capsys.readouterr().out
    assert len(instances) == 1
    assert session._watcher is instances[0]
    assert "*.py" in out
    assert "pytest" in out


@pytest.mark.asyncio
async def test_handle_command_persists_mcp_runtime_across_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        (workspace / ".git").mkdir()
        _write_mcp_definition(workspace)
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace)
        session = ChatSession(MagicMock(), config=BeepConfig())

        await session._handle_command("/mcp status")
        first_state = session._mcp_runtime_state
        await session._handle_command("/mcp tools")

    assert first_state is not None
    assert session._mcp_runtime_state is first_state
    assert first_state.owner == "chat-session"
    assert first_state.client is not None
    assert first_state.resolution is not None
    assert [tool.name for tool in first_state.client.list_tools()] == ["demo_tool"]


@pytest.mark.asyncio
async def test_handle_command_stores_mcp_client_error_on_session_state(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from beep.mcp.client import MCPClient

    def _boom(_cls, _servers):
        raise RuntimeError("mcp boom")

    from beep.app_service import AppService

    AppService.reset_registry()
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        (workspace / ".git").mkdir()
        _write_mcp_definition(workspace)
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace)
        monkeypatch.setattr(MCPClient, "from_config", classmethod(_boom))
        session = ChatSession(MagicMock(), config=BeepConfig())

        await session._handle_command("/mcp status")

    out = capsys.readouterr().out
    assert "mcp boom" in out
    assert session._mcp_runtime_state is not None
    assert session._mcp_runtime_state.client is None
    assert session._mcp_runtime_state.client_error == "mcp boom"
