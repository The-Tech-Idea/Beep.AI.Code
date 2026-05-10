"""Tests for diagnostics command guardrails."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.exceptions import Exit

from beep.commands.diagnostics import diagnostics_cmd, doctor_cmd


def test_diagnostics_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.config.load_config", side_effect=RuntimeError("boom")):
        with pytest.raises(Exit):
            diagnostics_cmd()
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_diagnostics_cmd_prints_summary(capsys) -> None:
    config = SimpleNamespace(
        is_configured=True,
        server_url="http://localhost:8000",
        default_model="test-model",
        max_tokens=4096,
        temperature=0.2,
        mcp_enabled=False,
        mcp_servers=[],
    )
    plugin_runtime = SimpleNamespace(
        loaded_count=0,
        searched_paths=[],
        registry=SimpleNamespace(get_load_errors=lambda: []),
    )
    with patch("beep.config.load_config", return_value=config):
        with patch("beep.workspace.detector.find_workspace_root", return_value="."):
            with patch("beep.workspace.git.is_git_repo", return_value=True):
                with patch("beep.utils.json_logging.is_json_logging_enabled", return_value=False):
                    with patch(
                        "beep.plugins.runtime.load_runtime_plugins",
                        return_value=plugin_runtime,
                    ):
                        with patch(
                            "beep.commands.diagnostics._inspect_config_schema",
                            return_value={"status": "current", "reason": "ok"},
                        ):
                            with patch(
                                "beep.commands.diagnostics._collect_agent_runtime_status",
                                return_value={
                                    "status": "ready",
                                    "compatibility_status": "current",
                                    "repair_command": None,
                                    "repair_reason": "Managed agent runtime is current.",
                                },
                            ):
                                with patch(
                                    "beep.commands.diagnostics._inspect_session_history_schema",
                                    return_value={"status": "current", "reason": "ok"},
                                ):
                                    with patch(
                                        "beep.commands.diagnostics._inspect_workspace_session_memory_schema",
                                        return_value={"status": "absent", "reason": "none"},
                                    ):
                                        diagnostics_cmd()
    out = capsys.readouterr().out
    assert "Diagnostics" in out
    assert "Doctor Summary" in out
    assert "Repair Guidance" in out
    assert "Plugins loaded: 0" in out


def test_diagnostics_cmd_prints_repair_guidance(capsys) -> None:
    config = SimpleNamespace(
        is_configured=False,
        server_url="http://localhost:8000",
        default_model=None,
        max_tokens=4096,
        temperature=0.2,
        mcp_enabled=False,
        mcp_servers=[],
    )
    plugin_runtime = SimpleNamespace(
        loaded_count=0,
        searched_paths=[],
        registry=SimpleNamespace(get_load_errors=lambda: []),
    )
    with patch("beep.config.load_config", return_value=config):
        with patch("beep.workspace.detector.find_workspace_root", return_value="."):
            with patch("beep.workspace.git.is_git_repo", return_value=True):
                with patch("beep.utils.json_logging.is_json_logging_enabled", return_value=False):
                    with patch(
                        "beep.plugins.runtime.load_runtime_plugins",
                        return_value=plugin_runtime,
                    ):
                        with patch(
                            "beep.commands.diagnostics._inspect_config_schema",
                            return_value={"status": "current", "reason": "ok"},
                        ):
                            with patch(
                                "beep.commands.diagnostics._collect_agent_runtime_status",
                                return_value={
                                    "status": "error",
                                    "compatibility_status": "stale",
                                    "repair_command": "beep agent reinstall runtime",
                                    "repair_reason": "Rebuild the managed runtime from scratch.",
                                },
                            ):
                                with patch(
                                    "beep.commands.diagnostics._inspect_session_history_schema",
                                    return_value={"status": "legacy", "reason": "legacy histories"},
                                ):
                                    with patch(
                                        "beep.commands.diagnostics._inspect_workspace_session_memory_schema",
                                        return_value={
                                            "status": "corrupt",
                                            "reason": "corrupt session memory",
                                            "path": ".beep/session_memory.json",
                                        },
                                    ):
                                        diagnostics_cmd()
    normalized = " ".join(capsys.readouterr().out.split())
    assert "beep setup" in normalized
    assert "beep agent reinstall runtime" in normalized
    assert ".beep/session_memory.json" in normalized


def test_doctor_cmd_fix_runs_supported_runtime_refresh(capsys) -> None:
    config = SimpleNamespace(
        is_configured=True,
        server_url="http://localhost:8000",
        default_model="test-model",
        max_tokens=4096,
        temperature=0.2,
        mcp_enabled=False,
        mcp_servers=[],
    )
    plugin_runtime = SimpleNamespace(
        loaded_count=0,
        searched_paths=[],
        registry=SimpleNamespace(get_load_errors=lambda: []),
    )
    with patch("beep.config.load_config", return_value=config):
        with patch("beep.workspace.detector.find_workspace_root", return_value="."):
            with patch("beep.workspace.git.is_git_repo", return_value=True):
                with patch("beep.utils.json_logging.is_json_logging_enabled", return_value=False):
                    with patch(
                        "beep.plugins.runtime.load_runtime_plugins",
                        return_value=plugin_runtime,
                    ):
                        with patch(
                            "beep.commands.diagnostics._inspect_config_schema",
                            return_value={"status": "current", "reason": "ok"},
                        ):
                            with patch(
                                "beep.commands.diagnostics._collect_agent_runtime_status",
                                return_value={
                                    "status": "error",
                                    "compatibility_status": "stale",
                                    "repair_command": "beep agent setup",
                                    "repair_reason": "Refresh the managed runtime.",
                                },
                            ):
                                with patch(
                                    "beep.commands.diagnostics._inspect_session_history_schema",
                                    return_value={"status": "current", "reason": "ok"},
                                ):
                                    with patch(
                                        "beep.commands.diagnostics._inspect_workspace_session_memory_schema",
                                        return_value={"status": "absent", "reason": "none"},
                                    ):
                                        with patch("beep.commands.agent.agent_setup_cmd") as agent_setup_cmd:
                                            doctor_cmd(fix=True)
    out = capsys.readouterr().out
    assert "Applying Supported Repairs" in out
    agent_setup_cmd.assert_called_once_with()


def test_doctor_cmd_fix_fails_when_only_manual_repairs_exist() -> None:
    config = SimpleNamespace(
        is_configured=False,
        server_url="http://localhost:8000",
        default_model=None,
        max_tokens=4096,
        temperature=0.2,
        mcp_enabled=False,
        mcp_servers=[],
    )
    plugin_runtime = SimpleNamespace(
        loaded_count=0,
        searched_paths=[],
        registry=SimpleNamespace(get_load_errors=lambda: []),
    )
    with patch("beep.config.load_config", return_value=config):
        with patch("beep.workspace.detector.find_workspace_root", return_value="."):
            with patch("beep.workspace.git.is_git_repo", return_value=True):
                with patch("beep.utils.json_logging.is_json_logging_enabled", return_value=False):
                    with patch(
                        "beep.plugins.runtime.load_runtime_plugins",
                        return_value=plugin_runtime,
                    ):
                        with patch(
                            "beep.commands.diagnostics._inspect_config_schema",
                            return_value={"status": "current", "reason": "ok"},
                        ):
                            with patch(
                                "beep.commands.diagnostics._collect_agent_runtime_status",
                                return_value={
                                    "status": "ready",
                                    "compatibility_status": "current",
                                    "repair_command": None,
                                    "repair_reason": "Managed agent runtime is current.",
                                },
                            ):
                                with patch(
                                    "beep.commands.diagnostics._inspect_session_history_schema",
                                    return_value={"status": "current", "reason": "ok"},
                                ):
                                    with patch(
                                        "beep.commands.diagnostics._inspect_workspace_session_memory_schema",
                                        return_value={
                                            "status": "corrupt",
                                            "reason": "corrupt session memory",
                                            "path": ".beep/session_memory.json",
                                        },
                                    ):
                                        with pytest.raises(Exit):
                                            doctor_cmd(fix=True)
