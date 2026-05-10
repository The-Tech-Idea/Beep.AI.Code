"""Tests for the sub-agent dispatcher and related modules."""

from __future__ import annotations

from pathlib import Path
import tempfile
import pytest

from beep.agent.subagents.dispatcher import (
    SubAgentDispatcher,
    SubAgentResult,
    VALID_SUBAGENT_TYPES,
)
from beep.agent.subagents.explore_agent import EXPLORE_TOOLS, EXPLORE_SYSTEM_PROMPT_SUFFIX
from beep.agent.subagents.plan_agent import PLAN_TOOLS, PLAN_SYSTEM_PROMPT_SUFFIX
from beep.agent.subagents.result_formatter import format_subagent_result
from beep.agent.tools.base import BaseTool, ToolResult


class FakeTool(BaseTool):
    def __init__(self, name: str, read_only_safe: bool = True) -> None:
        self._name = name
        self._read_only_safe = read_only_safe

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Fake tool: {self._name}"

    @property
    def parameters(self) -> dict:
        return {}

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output="ok")

    @property
    def read_only_safe(self) -> bool:
        return self._read_only_safe


class TestSubAgentDispatcher:
    def test_can_spawn_when_depth_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dispatcher = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=[],
                current_depth=0,
                max_depth=1,
            )
            assert dispatcher.can_spawn() is True

    def test_cannot_spawn_when_depth_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dispatcher = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=[],
                current_depth=1,
                max_depth=1,
            )
            assert dispatcher.can_spawn() is False

    def test_prepare_dispatch_explore(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tools = [
                FakeTool("file_read"),
                FakeTool("search"),
                FakeTool("file_write", read_only_safe=False),
            ]
            dispatcher = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=tools,
            )
            result = dispatcher.prepare_dispatch(
                goal="Find auth module",
                subagent_type="explore",
                backend=None,
                system_prompt="test prompt",
                session_id="sess-1",
            )
            assert result.success is True
            assert result.subagent_type == "explore"
            assert result.goal == "Find auth module"
            # Should only include explore tools
            tool_names = {t.name for t in result._tools}
            assert "file_read" in tool_names
            assert "search" in tool_names
            assert "file_write" not in tool_names

    def test_prepare_dispatch_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tools = [
                FakeTool("file_read"),
                FakeTool("todo_write"),
                FakeTool("shell", read_only_safe=False),
            ]
            dispatcher = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=tools,
            )
            result = dispatcher.prepare_dispatch(
                goal="Plan refactoring",
                subagent_type="plan",
                backend=None,
                system_prompt="test prompt",
                session_id="sess-1",
            )
            assert result.success is True
            tool_names = {t.name for t in result._tools}
            assert "file_read" in tool_names
            assert "todo_write" in tool_names
            assert "shell" not in tool_names

    def test_prepare_dispatch_general(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tools = [FakeTool("file_read"), FakeTool("shell")]
            dispatcher = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=tools,
            )
            result = dispatcher.prepare_dispatch(
                goal="Do everything",
                subagent_type="general",
                backend=None,
                system_prompt="test prompt",
                session_id="sess-1",
            )
            assert result.success is True
            # General gets all tools
            assert len(result._tools) == 2

    def test_prepare_dispatch_invalid_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dispatcher = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=[],
            )
            result = dispatcher.prepare_dispatch(
                goal="test",
                subagent_type="invalid",
                backend=None,
                system_prompt="",
                session_id="",
            )
            assert result.success is False
            assert "Unknown sub-agent type" in result.summary

    def test_prepare_dispatch_depth_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dispatcher = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=[],
                current_depth=1,
                max_depth=1,
            )
            result = dispatcher.prepare_dispatch(
                goal="test",
                subagent_type="explore",
                backend=None,
                system_prompt="",
                session_id="",
            )
            assert result.success is False
            assert "maximum depth" in result.summary

    def test_valid_subagent_types(self) -> None:
        assert "explore" in VALID_SUBAGENT_TYPES
        assert "plan" in VALID_SUBAGENT_TYPES
        assert "general" in VALID_SUBAGENT_TYPES

    def test_child_dispatcher_depth_increments(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tools = [FakeTool("file_read")]
            parent = SubAgentDispatcher(
                workspace_root=Path(td),
                all_tools=tools,
                current_depth=0,
                max_depth=2,
            )
            result = parent.prepare_dispatch(
                goal="test",
                subagent_type="explore",
                backend=None,
                system_prompt="",
                session_id="",
            )
            assert result._dispatcher is not None
            assert result._dispatcher._current_depth == 1
            # Child can still spawn since max_depth=2
            assert result._dispatcher.can_spawn() is True


class TestExploreAgent:
    def test_explore_tools_are_read_only(self) -> None:
        read_only_names = {
            "file_read",
            "search",
            "glob_files",
            "list_directory",
            "context",
            "code_snippet_list",
            "todo_write",
        }
        assert EXPLORE_TOOLS.issubset(read_only_names)

    def test_explore_system_prompt_suffix(self) -> None:
        assert "exploration" in EXPLORE_SYSTEM_PROMPT_SUFFIX.lower()
        assert "CANNOT write" in EXPLORE_SYSTEM_PROMPT_SUFFIX


class TestPlanAgent:
    def test_plan_tools_are_read_only(self) -> None:
        read_only_names = {
            "file_read",
            "search",
            "glob_files",
            "list_directory",
            "context",
            "todo_write",
        }
        assert PLAN_TOOLS.issubset(read_only_names)

    def test_plan_system_prompt_suffix(self) -> None:
        assert "planning" in PLAN_SYSTEM_PROMPT_SUFFIX.lower()
        assert "CANNOT write" in PLAN_SYSTEM_PROMPT_SUFFIX


class TestResultFormatter:
    def test_basic_summary(self) -> None:
        summary = format_subagent_result(
            name="explore",
            goal="Find auth module",
            steps_executed=5,
            final_message="Found auth.py with OAuth2",
            todo_list=None,
        )
        assert "[EXPLORE SUB-AGENT]" in summary
        assert "Find auth module" in summary
        assert "Steps executed: 5" in summary
        assert "Found auth.py" in summary

    def test_todo_list_summary(self) -> None:
        todo_list = {
            "1": {"content": "Read files", "status": "completed"},
            "2": {"content": "Analyze", "status": "pending"},
        }
        summary = format_subagent_result(
            name="plan",
            goal="Plan refactor",
            steps_executed=3,
            final_message="Done planning",
            todo_list=todo_list,
        )
        assert "Tasks completed: 1/2" in summary

    def test_truncates_long_message(self) -> None:
        long_message = "x" * 1000
        summary = format_subagent_result(
            name="explore",
            goal="test",
            steps_executed=1,
            final_message=long_message,
            todo_list=None,
        )
        assert len(summary) <= 500
        assert "..." in summary

    def test_empty_message(self) -> None:
        summary = format_subagent_result(
            name="plan",
            goal="test",
            steps_executed=2,
            final_message=None,
            todo_list=None,
        )
        assert "[PLAN SUB-AGENT]" in summary
        assert "Steps executed: 2" in summary
