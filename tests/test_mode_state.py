"""Tests for Plan/Build mode state."""

from __future__ import annotations

import pytest

from beep.chat.mode_state import (
    AgentMode,
    BANNER_BUILD,
    BANNER_PLAN,
    MODE_TO_SANDBOX,
    SANDBOX_TO_MODE,
    build_mode_banner,
    is_read_only_tool,
    is_write_tool,
)
from beep.permissions.manager import SandboxMode


class TestAgentMode:
    def test_values(self) -> None:
        assert AgentMode.PLAN == "plan"
        assert AgentMode.BUILD == "build"

    def test_mode_to_sandbox(self) -> None:
        assert MODE_TO_SANDBOX[AgentMode.PLAN] == SandboxMode.READ_ONLY
        assert MODE_TO_SANDBOX[AgentMode.BUILD] == SandboxMode.WORKSPACE_WRITE

    def test_sandbox_to_mode(self) -> None:
        assert SANDBOX_TO_MODE[SandboxMode.READ_ONLY] == AgentMode.PLAN
        assert SANDBOX_TO_MODE[SandboxMode.WORKSPACE_WRITE] == AgentMode.BUILD
        assert SANDBOX_TO_MODE[SandboxMode.FULL_TRUST] == AgentMode.BUILD


class TestBanners:
    def test_plan_banner(self) -> None:
        assert "PLAN MODE" in BANNER_PLAN

    def test_build_banner(self) -> None:
        assert "BUILD MODE" in BANNER_BUILD

    def test_build_mode_banner(self) -> None:
        assert build_mode_banner(AgentMode.PLAN) == BANNER_PLAN
        assert build_mode_banner(AgentMode.BUILD) == BANNER_BUILD


class TestToolClassification:
    def test_read_only_tools(self) -> None:
        assert is_read_only_tool("file_read") is True
        assert is_read_only_tool("search") is True
        assert is_read_only_tool("semantic_search") is True

    def test_write_tools(self) -> None:
        assert is_write_tool("file_write") is True
        assert is_write_tool("file_edit") is True
        assert is_write_tool("shell") is True

    def test_read_only_tool_not_write(self) -> None:
        assert is_write_tool("file_read") is False
        assert is_write_tool("search") is False

    def test_write_tool_not_read_only(self) -> None:
        assert is_read_only_tool("file_write") is False
        assert is_read_only_tool("shell") is False

    def test_unknown_tool(self) -> None:
        assert is_read_only_tool("nonexistent") is False
        assert is_write_tool("nonexistent") is False
