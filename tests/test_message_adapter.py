"""Tests for the LangGraph tool node construction and message adapter integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from beep.agent.graph import AgentGraphRunner
from beep.permissions.manager import SandboxMode
from unittest.mock import AsyncMock


class _FakeToolNode:
    last_instance: "_FakeToolNode | None" = None
    next_result: dict[str, object] = {"messages": []}

    def __init__(self, tools: list[object]) -> None:
        self.tools = tools
        self.ainvoke = AsyncMock(return_value=self.__class__.next_result)
        _FakeToolNode.last_instance = self


def _runner(
    tool: object,
    *,
    auto_approve: bool = True,
    sandbox_mode: SandboxMode = SandboxMode.WORKSPACE_WRITE,
    tool_node_cls: object | None = _FakeToolNode,
) -> AgentGraphRunner:
    return AgentGraphRunner(
        backend=MagicMock(),
        tools=[tool],
        workspace_root=Path.cwd(),
        max_steps=5,
        max_tool_calls_per_step=3,
        max_tool_calls_total=10,
        step_timeout=30.0,
        max_repeated_calls=3,
        max_consecutive_failures=2,
        max_tool_output_chars=4000,
        auto_approve=auto_approve,
        sandbox_mode=sandbox_mode,
        system_prompt="system prompt",
        workspace_rules=[],
        session_id="thread-test",
        tool_node_cls=tool_node_cls,
    )


@pytest.mark.asyncio
async def test_graph_runner_builds_langgraph_tool_node_with_embedded_approval_disabled() -> None:
    raw_tool = MagicMock()
    raw_tool.name = "file_read"
    runner = _runner(raw_tool)

    adapted_tool = object()
    deps = runner._deps
    fake_adapt_tools = MagicMock(return_value=[adapted_tool])
    from dataclasses import replace

    runner._deps = replace(deps, adapt_tools=fake_adapt_tools)
    tool_node = runner._get_langgraph_tool_node()

    assert tool_node is _FakeToolNode.last_instance
    assert _FakeToolNode.last_instance is not None
    assert _FakeToolNode.last_instance.tools == [adapted_tool]
    fake_adapt_tools.assert_called_once_with(
        [raw_tool],
        max_output_chars=4000,
        require_human_approval=False,
    )
