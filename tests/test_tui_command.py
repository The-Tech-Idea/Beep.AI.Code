"""Tests for TUI command entrypoint guards."""

from __future__ import annotations

from unittest.mock import patch

from beep.commands.tui import tui_cmd
from beep.config import BeepConfig


def _mock_config() -> BeepConfig:
    return BeepConfig(
        server_url="http://localhost:8000",
        api_token="token",
        default_model="test-model",
    )


def test_tui_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.tui.app.run_tui", side_effect=RuntimeError("boom")):
            tui_cmd(model=None, mode="assistant")
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_tui_cmd_handles_keyboard_interrupt(capsys) -> None:
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.tui.app.run_tui", side_effect=KeyboardInterrupt):
            tui_cmd(model=None, mode="assistant")
    out = capsys.readouterr().out
    assert "tui closed" in out.lower()
