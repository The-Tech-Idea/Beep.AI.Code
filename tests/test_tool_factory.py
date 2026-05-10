"""Tests for the agent tool factory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from beep.agent.tools.factory import build_agent_tools, get_default_tools


class _FakePluginRuntime:
    def __init__(self) -> None:
        self.registry = MagicMock()
        self.registry.get_tools.return_value = []


@pytest.fixture
def plugin_runtime() -> _FakePluginRuntime:
    return _FakePluginRuntime()


def test_get_default_tools_returns_read_only_tools() -> None:
    tools = get_default_tools(Path.cwd(), read_only=True)
    names = [t.name for t in tools]
    assert "file_read" in names
    assert "search" in names
    assert "todo_write" in names
    assert "dispatch_agent" in names
    assert "file_write" not in names
    assert "file_edit" not in names
    assert "shell" not in names


def test_get_default_tools_returns_write_tools_when_not_read_only() -> None:
    tools = get_default_tools(Path.cwd(), read_only=False)
    names = [t.name for t in tools]
    assert "file_write" in names
    assert "file_edit" in names
    assert "shell" in names


def test_get_default_tools_injects_todo_list() -> None:
    from beep.agent.planning import TodoList

    todo = TodoList()
    todo.replace([{"id": "1", "content": "Do something", "status": "pending"}])
    tools = get_default_tools(Path.cwd(), todo_list=todo)
    todo_tool = next(t for t in tools if t.name == "todo_write")
    assert todo_tool._todo_list is todo
    assert len(todo_tool._todo_list) == 1


def test_get_default_tools_injects_subagent_dispatcher() -> None:
    dispatcher = MagicMock()
    tools = get_default_tools(Path.cwd(), subagent_dispatcher=dispatcher)
    dispatch_tool = next(t for t in tools if t.name == "dispatch_agent")
    assert dispatch_tool._dispatcher is dispatcher


def test_build_agent_tools_extends_default_tools(plugin_runtime: _FakePluginRuntime) -> None:
    tools = build_agent_tools(
        workspace_root=Path.cwd(),
        plugin_runtime=plugin_runtime,
        mcp_enabled=False,
    )
    names = {t.name for t in tools}
    assert "file_read" in names
    assert "file_write" in names


def test_build_agent_tools_filters_read_only(plugin_runtime: _FakePluginRuntime) -> None:
    tools = build_agent_tools(
        workspace_root=Path.cwd(),
        plugin_runtime=plugin_runtime,
        read_only=True,
    )
    for t in tools:
        module = type(t).__module__
        if module.startswith("beep.agent.tools."):
            assert getattr(t, "read_only_safe", False) is True
