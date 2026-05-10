"""Tests for one-shot CLI commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from beep.commands.ask import ask_cmd
from beep.commands.review import review_cmd
from beep.config import BeepConfig


def _mock_config() -> BeepConfig:
    return BeepConfig(
        server_url="http://localhost:8000",
        api_token="token",
        default_model="test-model",
    )


def _mock_project_config() -> BeepConfig:
    return BeepConfig(
        server_url="http://localhost:8000",
        api_token="token",
        default_model="test-model",
        project_id=77,
    )


def _patch_api_client(client):
    """Patch AppService.api_client to return the given mock client."""
    from beep.app_service import AppService

    def _mock_api_client(_self, config):
        return client

    return patch.object(AppService, "api_client", _mock_api_client)


def test_ask_command_handles_empty_model_output(capsys) -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(return_value={"choices": [{"message": {"content": "   "}}]})

    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with _patch_api_client(client):
            ask_cmd(question="hello", model=None, mode="assistant")

    out = capsys.readouterr().out
    assert "empty response" in out.lower()


def test_ask_command_attaches_coding_workspace_metadata() -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(
        return_value={"choices": [{"message": {"content": "answer"}}]}
    )

    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.commands.ask.find_workspace_root") as root_mock:
            root_mock.return_value = "C:/repo"
            with _patch_api_client(client):
                ask_cmd(question="hello", model=None, mode="assistant")

    _, kwargs = client.chat_completion.call_args
    assert kwargs["coding_assistant"] == {
        "workspace_root": "C:/repo",
        "interaction_mode": "inline",
    }
    assert "Beep.AI.Code" in kwargs["messages"][0]["content"]


def test_ask_command_uses_configured_project_id() -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(
        return_value={"choices": [{"message": {"content": "answer"}}]}
    )

    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_project_config()):
        with patch("beep.commands.ask.find_workspace_root", return_value="C:/repo"):
            with _patch_api_client(client):
                ask_cmd(question="hello", model=None, mode="assistant")

    _, kwargs = client.chat_completion.call_args
    assert kwargs["coding_assistant"] == {
        "workspace_root": "C:/repo",
        "interaction_mode": "inline",
        "project_id": 77,
    }


def test_review_command_handles_empty_model_output(capsys) -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(return_value={"choices": [{"message": {"content": ""}}]})

    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.workspace.detector.find_workspace_root") as root_mock:
            root_mock.return_value = MagicMock()
            with patch("beep.commands.review.get_diff_to_review", return_value="diff --git a b"):
                with _patch_api_client(client):
                    review_cmd(staged=True, file=None, model=None)

    out = capsys.readouterr().out
    assert "empty review" in out.lower()


def test_ask_command_handles_keyboard_interrupt(capsys) -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(side_effect=KeyboardInterrupt)
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with _patch_api_client(client):
            ask_cmd(question="hello", model=None, mode="assistant")
    out = capsys.readouterr().out
    assert "ask cancelled" in out.lower()


def test_review_command_handles_keyboard_interrupt(capsys) -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(side_effect=KeyboardInterrupt)
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.workspace.detector.find_workspace_root", return_value=MagicMock()):
            with patch("beep.commands.review.get_diff_to_review", return_value="diff --git a b"):
                with _patch_api_client(client):
                    review_cmd(staged=True, file=None, model=None)
    out = capsys.readouterr().out
    assert "review cancelled" in out.lower()


def test_ask_command_handles_api_error(capsys) -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with _patch_api_client(client):
            ask_cmd(question="hello", model=None, mode="assistant")
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_review_command_handles_api_error(capsys) -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.workspace.detector.find_workspace_root", return_value=MagicMock()):
            with patch("beep.commands.review.get_diff_to_review", return_value="diff --git a b"):
                with _patch_api_client(client):
                    review_cmd(staged=True, file=None, model=None)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()
