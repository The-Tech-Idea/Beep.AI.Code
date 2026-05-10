"""Integration-level plugin wiring tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from beep.chat.repl import ChatSession
from beep.plugins.runtime import load_runtime_plugins


def _write_workspace_plugin(plugin_dir: Path) -> None:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.joinpath("integration_plugin.py").write_text(
        """
from beep.plugins.registry import CommandPlugin, PluginInfo

class IntegrationPlugin(CommandPlugin):
    info = PluginInfo(name="integration-plugin", version="1.0.0", description="integration")

    def activate(self): ...

    def get_commands(self):
        return {"ping": "plugin ping command"}

    async def handle_command(self, command: str, args: str):
        return f"pong:{args}"
""",
        encoding="utf-8",
    )


def test_runtime_loads_workspace_plugins() -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        _write_workspace_plugin(workspace_root / ".beep" / "plugins")
        runtime = load_runtime_plugins(workspace_root)
        names = {plugin["name"] for plugin in runtime.registry.list_plugins()}
    assert "integration-plugin" in names
    assert runtime.loaded_count == 1


@pytest.mark.asyncio
async def test_chat_session_routes_unknown_slash_to_plugin(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        _write_workspace_plugin(workspace_root / ".beep" / "plugins")
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace_root)
        session = ChatSession(MagicMock())
        await session._handle_command("/ping hello")
    output = capsys.readouterr().out
    assert "pong:hello" in output
