"""Tests for runtime guards on command entrypoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from beep.commands.lint import lint_cmd
from beep.commands.rag import rag_collections_cmd, rag_query_cmd
from beep.commands.test import test_cmd as run_test_cmd
from beep.config import BeepConfig


def _mock_config() -> BeepConfig:
    return BeepConfig(
        server_url="http://localhost:8000",
        api_token="token",
        default_model="test-model",
    )


def test_lint_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.workspace.detector.find_workspace_root", return_value=MagicMock()):
        with patch("beep.commands.lint.detect_linters", return_value=[]):
            with patch(
                    "beep.commands.lint.run_lint",
                    new=AsyncMock(side_effect=RuntimeError("boom")),
                ):
                lint_cmd(file=None, fix=False, linter=None)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_test_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.workspace.detector.find_workspace_root", return_value=MagicMock()):
        with patch("beep.commands.test.detect_framework") as detect:
            detect.return_value = MagicMock(value="pytest")
            with patch(
                    "beep.commands.test.run_tests",
                    new=AsyncMock(side_effect=RuntimeError("boom")),
                ):
                run_test_cmd(file=None, watch=False, framework=None, timeout=30)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_rag_query_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch(
                    "beep.commands.rag.semantic_search",
                    new=AsyncMock(side_effect=RuntimeError("boom")),
                ):
            rag_query_cmd(query="hello", collection=None, max_results=3)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_rag_collections_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch(
                    "beep.commands.rag.list_collections",
                    new=AsyncMock(side_effect=RuntimeError("boom")),
                ):
            rag_collections_cmd()
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()
