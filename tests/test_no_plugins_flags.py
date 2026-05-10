"""Tests that --no-plugins flag is plumbed into chat/agent runtimes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from beep.chat.commands.agent import AgentCommand
from beep.commands.agent import agent_cmd, agent_resume_cmd
from beep.commands.chat import chat_cmd
from beep.config import BeepConfig
from beep.permissions.manager import SandboxMode
from pathlib import Path


def _mock_config() -> BeepConfig:
    return BeepConfig(
        server_url="http://localhost:8000",
        api_token="token",
        default_model="test-model",
    )


def test_chat_cmd_passes_plugins_enabled_false() -> None:
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.commands.chat.run_chat", new=AsyncMock()) as run_chat_mock:
            chat_cmd(model=None, mode="assistant", show_tokens=False, resume=None, no_plugins=True)
            assert run_chat_mock.await_count == 1
            kwargs = run_chat_mock.await_args.kwargs
            assert kwargs["plugins_enabled"] is False


def test_agent_cmd_passes_plugins_enabled_false() -> None:
    with patch("beep.commands.agent.ensure_agent_configured", return_value=_mock_config()):
        with patch("beep.commands.agent.run_agent", new=AsyncMock()) as run_agent_mock:
            agent_cmd(goal="test", max_steps=1, auto_approve=True, model=None, no_plugins=True)
            assert run_agent_mock.await_count == 1
            kwargs = run_agent_mock.await_args.kwargs
            assert kwargs["plugins_enabled"] is False
            assert kwargs["sandbox_mode"] == SandboxMode.WORKSPACE_WRITE


def test_agent_cmd_forwards_configured_project_metadata() -> None:
    config = _mock_config().model_copy(update={"project_id": 91})
    with patch("beep.commands.agent.ensure_agent_configured", return_value=config):
        with patch("beep.commands.agent.find_workspace_root", return_value=Path("C:/repo")):
            with patch("beep.commands.agent.run_agent", new=AsyncMock()) as run_agent_mock:
                agent_cmd(goal="test", max_steps=1, auto_approve=True, model=None, no_plugins=False)
                assert run_agent_mock.await_count == 1
                kwargs = run_agent_mock.await_args.kwargs
                assert kwargs["coding_assistant"] == {
                    "workspace_root": str(Path("C:/repo")),
                    "interaction_mode": "agent",
                    "project_id": 91,
                }


def test_chat_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.setup_wizard.ensure_configured", return_value=_mock_config()):
        with patch("beep.commands.chat.run_chat", new=AsyncMock(side_effect=RuntimeError("boom"))):
            chat_cmd(model=None, mode="assistant", show_tokens=False, resume=None, no_plugins=False)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_agent_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.commands.agent.ensure_agent_configured", return_value=_mock_config()):
        with patch(
            "beep.commands.agent.run_agent", new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            agent_cmd(goal="test", max_steps=1, auto_approve=True, model=None, no_plugins=False)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_agent_cmd_uses_openai_compatible_backend_without_beep_client() -> None:
    config = _mock_config().model_copy(
        update={
            "agent_backend": "openai-compatible",
            "agent_base_url": "http://other-provider",
            "agent_api_key": "other-token",
            "agent_model": "other-model",
        }
    )
    with patch("beep.commands.agent.ensure_agent_configured", return_value=config):
        with patch("beep.commands.agent.BeepAPIClient") as client_cls:
            with patch("beep.commands.agent.run_agent", new=AsyncMock()) as run_agent_mock:
                agent_cmd(goal="test", max_steps=1, auto_approve=True, model=None, no_plugins=False)
    client_cls.assert_not_called()
    assert run_agent_mock.await_count == 1
    assert run_agent_mock.await_args.args[0] is None
    assert run_agent_mock.await_args.kwargs["config"] == config


def test_agent_resume_cmd_passes_plugins_enabled_false() -> None:
    with patch("beep.commands.agent.ensure_agent_configured", return_value=_mock_config()):
        with patch("beep.commands.agent.resume_agent", new=AsyncMock()) as resume_agent_mock:
            agent_resume_cmd(session_id="thread-1", max_steps=1, auto_approve=True, model=None, no_plugins=True)
            assert resume_agent_mock.await_count == 1
            kwargs = resume_agent_mock.await_args.kwargs
            assert kwargs["plugins_enabled"] is False
            assert kwargs["sandbox_mode"] == SandboxMode.WORKSPACE_WRITE


def test_agent_resume_cmd_uses_openai_compatible_backend_without_beep_client() -> None:
    config = _mock_config().model_copy(
        update={
            "agent_backend": "openai-compatible",
            "agent_base_url": "http://other-provider",
            "agent_api_key": "other-token",
            "agent_model": "other-model",
        }
    )
    with patch("beep.commands.agent.ensure_agent_configured", return_value=config):
        with patch("beep.commands.agent.BeepAPIClient") as client_cls:
            with patch("beep.commands.agent.resume_agent", new=AsyncMock()) as resume_agent_mock:
                agent_resume_cmd(session_id="thread-1", max_steps=1, auto_approve=True, model=None, no_plugins=False)
    client_cls.assert_not_called()
    assert resume_agent_mock.await_count == 1
    assert resume_agent_mock.await_args.args[0] is None
    assert resume_agent_mock.await_args.args[1] == "thread-1"
    assert resume_agent_mock.await_args.kwargs["config"] == config


@pytest.mark.asyncio
async def test_chat_agent_command_inherits_runtime_flags() -> None:
    cmd = AgentCommand()
    config = _mock_config().model_copy(update={"mcp_enabled": True})
    config.mcp_servers = []
    ctx = {
        "client": object(),
        "session": SimpleNamespace(plugins_enabled=False, _sandbox_mode=SandboxMode.READ_ONLY),
        "config": config,
    }
    with patch("beep.agent.loop.run_agent", new=AsyncMock()) as run_agent_mock:
        await cmd.execute("fix lint", ctx)
        kwargs = run_agent_mock.await_args.kwargs
        assert kwargs["plugins_enabled"] is False
        assert kwargs["mcp_enabled"] is True
        assert kwargs["sandbox_mode"] == SandboxMode.READ_ONLY


@pytest.mark.asyncio
async def test_chat_agent_command_forwards_coding_metadata() -> None:
    cmd = AgentCommand()
    config = _mock_config().model_copy(update={"mcp_enabled": False})
    session = SimpleNamespace(
        plugins_enabled=True,
        _get_coding_metadata=lambda: {
            "project_id": 55,
            "session_id": "coding-55",
            "interaction_mode": "inline",
        },
    )
    ctx = {
        "client": object(),
        "session": session,
        "config": config,
    }
    with patch("beep.agent.loop.run_agent", new=AsyncMock()) as run_agent_mock:
        await cmd.execute("investigate tests", ctx)
        kwargs = run_agent_mock.await_args.kwargs
        assert kwargs["coding_assistant"]["project_id"] == 55
        assert kwargs["coding_assistant"]["session_id"] == "coding-55"
        assert kwargs["coding_assistant"]["interaction_mode"] == "agent"


@pytest.mark.asyncio
async def test_chat_agent_command_blocks_when_token_budget_reached() -> None:
    cmd = AgentCommand()
    config = _mock_config().model_copy(update={"mcp_enabled": False})
    session = SimpleNamespace(
        plugins_enabled=True,
        _max_token_budget=50,
        _token_count=50,
    )
    ctx = {
        "client": object(),
        "session": session,
        "config": config,
    }
    with patch("beep.agent.loop.run_agent", new=AsyncMock()) as run_agent_mock:
        await cmd.execute("investigate tests", ctx)
        run_agent_mock.assert_not_awaited()
