"""Tests for Plan/Build mode slash commands."""

from __future__ import annotations

from unittest.mock import MagicMock

from beep.chat.commands.mode import _set_mode
from beep.chat.mode_state import AgentMode
from beep.permissions.manager import SandboxMode


class TestSetMode:
    def test_sets_plan_mode(self) -> None:
        session = MagicMock()
        session._agent_mode = AgentMode.BUILD
        _set_mode(session, AgentMode.PLAN)
        assert session._agent_mode == AgentMode.PLAN
        assert session._sandbox_mode == SandboxMode.READ_ONLY
        assert session._sandbox is True

    def test_sets_build_mode(self) -> None:
        session = MagicMock()
        session._agent_mode = AgentMode.PLAN
        _set_mode(session, AgentMode.BUILD)
        assert session._agent_mode == AgentMode.BUILD
        assert session._sandbox_mode == SandboxMode.WORKSPACE_WRITE
        assert session._sandbox is False

    def test_plan_then_build(self) -> None:
        session = MagicMock()
        session._agent_mode = AgentMode.BUILD
        _set_mode(session, AgentMode.PLAN)
        assert session._agent_mode == AgentMode.PLAN
        _set_mode(session, AgentMode.BUILD)
        assert session._agent_mode == AgentMode.BUILD
