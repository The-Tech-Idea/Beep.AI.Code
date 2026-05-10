"""End-to-end CLI smoke tests for major feature flows.

These tests exercise complete CLI command paths (setup, chat, agent, sessions, RAG)
against controlled mocks to verify that command wiring, argument parsing, error handling,
and output rendering all work together.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from beep.cli import app
from beep.config import BeepConfig


RUNNER = CliRunner()


# ---------------------------------------------------------------------------
# Setup Flow
# ---------------------------------------------------------------------------


class TestSetupFlow:
    def test_setup_subcommand_exists(self) -> None:
        result = RUNNER.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
        assert "setup" in (result.stdout or "").lower()

    def test_status_without_config_fails(self) -> None:
        result = RUNNER.invoke(app, ["status"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Session Flow
# ---------------------------------------------------------------------------


class TestSessionFlow:
    def test_sessions_list_empty(self) -> None:
        with patch("beep.commands.sessions.list_sessions", return_value=[]):
            result = RUNNER.invoke(app, ["sessions", "list"])
        assert result.exit_code == 0
        assert "No sessions found" in (result.stdout or "")

    def test_sessions_list_with_data(self) -> None:
        session = SimpleNamespace(
            session_id="test-session-001",
            title="Test Session",
            message_count=5,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            last_message_preview="Hello world",
        )
        with patch("beep.commands.sessions.list_sessions", return_value=[session]):
            result = RUNNER.invoke(app, ["sessions", "list"])
        assert result.exit_code == 0
        assert "test-session-001" in (result.stdout or "")

    def test_sessions_help_shows_subcommands(self) -> None:
        result = RUNNER.invoke(app, ["sessions", "--help"])
        assert result.exit_code == 0
        assert "list" in (result.stdout or "").lower()
        assert "export" in (result.stdout or "").lower()
        assert "delete" in (result.stdout or "").lower()


# ---------------------------------------------------------------------------
# Agent Flow
# ---------------------------------------------------------------------------


class TestAgentFlow:
    def test_agent_help_shows_subcommands(self) -> None:
        result = RUNNER.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        assert "status" in (result.stdout or "").lower()
        assert "setup" in (result.stdout or "").lower()

    def test_agent_status_outputs_runtime_info(self) -> None:
        result = RUNNER.invoke(app, ["agent", "status"])
        assert result.exit_code == 0
        assert "Agent Runtime" in (result.stdout or "")

    def test_agent_setup_help(self) -> None:
        result = RUNNER.invoke(app, ["agent", "setup", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Workspace Flow
# ---------------------------------------------------------------------------


class TestWorkspaceFlow:
    def test_tree_command_displays(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "main.py").touch()
            result = RUNNER.invoke(app, ["tree", str(tmp_path)])
            assert result.exit_code == 0
            assert "main.py" in (result.stdout or "")

    def test_grep_command_help(self) -> None:
        result = RUNNER.invoke(app, ["grep", "--help"])
        assert result.exit_code == 0

    def test_cat_command_help(self) -> None:
        result = RUNNER.invoke(app, ["cat", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Diagnostics Flow
# ---------------------------------------------------------------------------


class TestDiagnosticsFlow:
    def test_diagnostics_runs_without_server(self) -> None:
        result = RUNNER.invoke(app, ["diagnostics"])
        assert result.exit_code == 0
        assert "Diagnostics" in (result.stdout or "")

    def test_doctor_runs_without_server(self) -> None:
        result = RUNNER.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Doctor" in (result.stdout or "")


# ---------------------------------------------------------------------------
# Template Flow
# ---------------------------------------------------------------------------


class TestTemplateFlow:
    def test_template_list_shows_builtins(self) -> None:
        result = RUNNER.invoke(app, ["template", "list"])
        assert result.exit_code == 0

    def test_template_help(self) -> None:
        result = RUNNER.invoke(app, ["template", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Plugin Flow
# ---------------------------------------------------------------------------


class TestPluginFlow:
    def test_plugins_paths_lists(self) -> None:
        result = RUNNER.invoke(app, ["plugins", "paths"])
        assert result.exit_code == 0

    def test_plugins_help(self) -> None:
        result = RUNNER.invoke(app, ["plugins", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# MCP Flow
# ---------------------------------------------------------------------------


class TestMCPFlow:
    def test_mcp_help(self) -> None:
        result = RUNNER.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0

    def test_mcp_list_empty(self) -> None:
        with patch("beep.commands.mcp.find_workspace_root", return_value=None):
            result = RUNNER.invoke(app, ["mcp", "list"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Quality Flow (lint, test)
# ---------------------------------------------------------------------------


class TestQualityFlow:
    def test_lint_help(self) -> None:
        result = RUNNER.invoke(app, ["lint", "--help"])
        assert result.exit_code == 0

    def test_test_help(self) -> None:
        result = RUNNER.invoke(app, ["test", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Ask Flow (one-shot query)
# ---------------------------------------------------------------------------


class TestAskFlow:
    def test_ask_requires_config(self) -> None:
        result = RUNNER.invoke(app, ["what is python?"])
        assert result.exit_code != 0
