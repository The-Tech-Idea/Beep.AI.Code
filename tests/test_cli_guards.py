"""Guardrail tests for top-level CLI commands."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from beep.cli import app


def test_status_closes_client_when_health_check_fails() -> None:
    runner = CliRunner()
    config = SimpleNamespace(server_url="http://localhost", is_configured=True)
    client = SimpleNamespace(
        health_check=AsyncMock(side_effect=RuntimeError("boom")),
        close=AsyncMock(),
    )
    with patch("beep.cli._require_config", return_value=config):
        with patch("beep.cli.BeepAPIClient", return_value=client):
            result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "connection failed" in (result.stdout or "").lower()
    assert client.close.await_count == 1


def test_config_set_rejects_invalid_max_tokens() -> None:
    runner = CliRunner()
    with patch("beep.cli.load_config", return_value=SimpleNamespace()):
        result = runner.invoke(app, ["config-set", "max_tokens", "abc"])
    assert result.exit_code == 1
    assert "must be an integer" in (result.stdout or "").lower()


def test_config_set_rejects_invalid_temperature() -> None:
    runner = CliRunner()
    with patch("beep.cli.load_config", return_value=SimpleNamespace()):
        result = runner.invoke(app, ["config-set", "temperature", "abc"])
    assert result.exit_code == 1
    assert "must be a number" in (result.stdout or "").lower()


def test_config_set_rejects_non_positive_max_tokens() -> None:
    runner = CliRunner()
    with patch("beep.cli.load_config", return_value=SimpleNamespace()):
        result = runner.invoke(app, ["config-set", "max_tokens", "0"])
    assert result.exit_code == 1
    assert "greater than 0" in (result.stdout or "").lower()


def test_config_set_rejects_out_of_range_temperature() -> None:
    runner = CliRunner()
    with patch("beep.cli.load_config", return_value=SimpleNamespace()):
        result = runner.invoke(app, ["config-set", "temperature", "3"])
    assert result.exit_code == 1
    assert "between 0 and 2" in (result.stdout or "").lower()


def test_config_set_handles_save_error() -> None:
    runner = CliRunner()
    with patch("beep.cli.load_config", return_value=SimpleNamespace()):
        with patch("beep.cli.save_config", side_effect=RuntimeError("disk full")):
            result = runner.invoke(app, ["config-set", "server_url", "http://localhost"])
    assert result.exit_code == 1
    assert "failed to save config: disk full" in (result.stdout or "").lower()


def test_config_set_accepts_custom_agent_backend_key() -> None:
    runner = CliRunner()
    config = SimpleNamespace()
    with patch("beep.cli.load_config", return_value=config):
        with patch("beep.cli.save_config") as save_config_mock:
            result = runner.invoke(app, ["config-set", "agent_backend", "custom-provider"])

    assert result.exit_code == 0
    assert getattr(config, "agent_backend") == "custom-provider"
    save_config_mock.assert_called_once()


def test_config_set_rejects_invalid_agent_reasoning_effort() -> None:
    runner = CliRunner()
    with patch("beep.cli.load_config", return_value=SimpleNamespace()):
        result = runner.invoke(app, ["config-set", "agent_reasoning_effort", "extreme"])
    assert result.exit_code == 1
    assert "must be one of" in (result.stdout or "").lower()


def test_config_set_accepts_agent_parallel_tool_calls_bool() -> None:
    runner = CliRunner()
    config = SimpleNamespace()
    with patch("beep.cli.load_config", return_value=config):
        with patch("beep.cli.save_config") as save_config_mock:
            result = runner.invoke(app, ["config-set", "agent_parallel_tool_calls", "false"])

    assert result.exit_code == 0
    assert getattr(config, "agent_parallel_tool_calls") is False
    save_config_mock.assert_called_once()


def test_config_set_rejects_non_positive_agent_thinking_budget_tokens() -> None:
    runner = CliRunner()
    with patch("beep.cli.load_config", return_value=SimpleNamespace()):
        result = runner.invoke(app, ["config-set", "agent_thinking_budget_tokens", "0"])
    assert result.exit_code == 1
    assert "greater than 0" in (result.stdout or "").lower()


def test_setup_handles_keyboard_interrupt() -> None:
    runner = CliRunner()
    with patch("beep.cli.run_setup_wizard", side_effect=KeyboardInterrupt):
        result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    assert "setup cancelled" in (result.stdout or "").lower()


def test_setup_handles_runtime_error() -> None:
    runner = CliRunner()
    with patch("beep.cli.run_setup_wizard", side_effect=RuntimeError("boom")):
        result = runner.invoke(app, ["setup"])
    assert result.exit_code == 1
    assert "setup failed: boom" in (result.stdout or "").lower()
