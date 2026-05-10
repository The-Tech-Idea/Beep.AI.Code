"""Lightweight CLI smoke checks (no live server required)."""

from __future__ import annotations

from typer.testing import CliRunner

from beep.cli import app


def test_cli_help_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = (result.stdout or "").lower()
    assert "beep" in out or "chat" in out or "setup" in out


def test_agent_subcommand_has_no_plugins_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["agent", "--help"])
    assert result.exit_code == 0
    assert "--no-plugins" in (result.stdout or "")
    assert "resume <thread_id>" in (result.stdout or "")


def test_cli_diagnostics_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["diagnostics"])
    assert result.exit_code == 0
    out = result.stdout or ""
    assert "Beep.AI.Code Diagnostics" in out or "Version:" in out
    assert "Plugin search paths:" in out


def test_cli_doctor_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    out = result.stdout or ""
    assert "Doctor Summary" in out
    assert "Repair Guidance" in out


def test_cli_self_update_help_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["self-update", "--help"])
    assert result.exit_code == 0
    assert "Print or execute the detected update workflow" in (result.stdout or "")


def test_cli_doctor_help_includes_fix() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "--fix" in (result.stdout or "")


def test_cli_unknown_flag_fails_fast() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--unknown-flag"])
    assert result.exit_code != 0
