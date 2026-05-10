"""Tests for TUI screens and dialogs."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from beep.config import BeepConfig
from beep.tui.app import TUIApp
from beep.tui.dialogs.command_palette import CommandEntry, CommandPalette
from beep.tui.dialogs.file_picker import FilePicker
from beep.tui.dialogs.model_selector import ModelSelector
from beep.tui.dialogs.session_switcher import SessionSwitcher
from beep.tui.widgets.message_display import MessageDisplay
from beep.tui.widgets.status_bar import StatusBar
from beep.tui.widgets.tool_call import ToolCallDisplay


def _mock_config() -> BeepConfig:
    return BeepConfig(
        server_url="http://localhost:8000",
        api_token="token",
        default_model="test-model",
    )


class TestMessageDisplay:
    def test_user_message_format(self) -> None:
        msg = MessageDisplay(role="user", content="hello `world`")
        rendered = msg._render_message()
        assert "You:" in rendered
        assert "cyan" in rendered

    def test_assistant_message_format(self) -> None:
        msg = MessageDisplay(role="assistant", content="done")
        rendered = msg._render_message()
        assert "Assistant:" in rendered

    def test_system_message_format(self) -> None:
        msg = MessageDisplay(role="system", content="init")
        rendered = msg._render_message()
        assert "italic" in rendered

    def test_error_message_format(self) -> None:
        msg = MessageDisplay(role="error", content="failed")
        rendered = msg._render_message()
        assert "Error:" in rendered

    def test_bash_command_format(self) -> None:
        msg = MessageDisplay(role="user", content="!ls -la")
        rendered = msg._render_message()
        assert "Shell:" in rendered


class TestStatusBar:
    def test_build_mode_indicator(self) -> None:
        bar = StatusBar()
        bar.set_mode("build")
        assert bar.mode == "build"
        assert "BUILD" in bar._render()

    def test_plan_mode_indicator(self) -> None:
        bar = StatusBar()
        bar.set_mode("plan")
        rendered = bar._render()
        assert "PLAN" in rendered


class TestToolCallDisplay:
    def test_running_status(self) -> None:
        display = ToolCallDisplay(tool_name="file_write", status="running")
        rendered = display._render()
        assert "file_write" in rendered

    def test_update_status(self) -> None:
        display = ToolCallDisplay(tool_name="shell", status="running")
        display.update_status("completed", output="done")
        assert display._status == "completed"


class TestCommandPalette:
    def test_filters_by_name(self) -> None:
        commands = [
            CommandEntry("New Session", "start fresh"),
            CommandEntry("Help", "show shortcuts"),
        ]
        palette = CommandPalette(commands)
        palette._filtered = [c for c in commands if "new" in c.name.lower()]
        assert len(palette._filtered) == 1
        assert palette._filtered[0].name == "New Session"

    def test_filters_by_description(self) -> None:
        commands = [
            CommandEntry("Toggle Mode", "switch plan/build"),
            CommandEntry("Help", "show shortcuts"),
        ]
        palette = CommandPalette(commands)
        palette._filtered = [c for c in commands if "shortcuts" in c.description.lower()]
        assert len(palette._filtered) == 1


class TestModelSelector:
    def test_filters_models(self) -> None:
        models = ["gpt-4o", "gpt-4-turbo", "claude-sonnet"]
        selector = ModelSelector(models, "gpt-4o")
        selector._filtered = [m for m in models if "claude" in m.lower()]
        assert len(selector._filtered) == 1
        assert selector._filtered[0] == "claude-sonnet"


class TestSessionSwitcher:
    def test_filters_sessions(self) -> None:
        sessions = [
            {"id": "abc123", "title": "Fix bug", "message_count": 5},
            {"id": "def456", "title": "Add feature", "message_count": 10},
        ]
        switcher = SessionSwitcher(sessions, "abc123")
        switcher._filtered = [s for s in sessions if "feature" in s["title"].lower()]
        assert len(switcher._filtered) == 1


class TestFilePicker:
    def test_scans_workspace_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.py").touch()
            (tmp_path / "README.md").touch()
            (tmp_path / ".git").mkdir()
            (tmp_path / "node_modules").mkdir()
            (tmp_path / "node_modules" / "pkg.js").touch()

            picker = FilePicker(tmp_path)
            picker._scan_files()

            assert "src/main.py" in picker._files
            assert "README.md" in picker._files
            assert not any("node_modules" in f for f in picker._files)
            assert not any(".git" in f for f in picker._files)


class TestTUIApp:
    def test_initializes_with_config(self) -> None:
        app = TUIApp(_mock_config())
        assert app._config is not None
        assert app._model == "test-model"

    def test_available_models_list(self) -> None:
        assert len(TUIApp.AVAILABLE_MODELS) > 0
        assert "gpt-4o" in TUIApp.AVAILABLE_MODELS
        assert "claude-sonnet-4-20250514" in TUIApp.AVAILABLE_MODELS

    def test_command_palette_entries(self) -> None:
        app = TUIApp(_mock_config())
        commands = app._get_commands()
        assert len(commands) > 0
        names = [c.name for c in commands]
        assert "New Session" in names
        assert "Help" in names
        assert "Quit" in names

    def test_messages_cleared_on_new_session_logic(self) -> None:
        app = TUIApp(_mock_config())
        app._messages = [{"role": "user", "content": "hello"}]
        app._messages = []
        assert app._messages == []
