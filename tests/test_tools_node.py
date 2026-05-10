"""Tests for the LangGraph agent tools node."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.agent.graph import AgentGraphRunner
from beep.permissions.manager import SandboxMode
from tests.test_agent_graph import _FakeAsyncSqliteSaver, _FakeStateGraph
from unittest.mock import AsyncMock


class _FakeToolNode:
    last_instance: "_FakeToolNode | None" = None
    next_result: dict[str, object] = {"messages": []}

    def __init__(self, tools: list[object]) -> None:
        self.tools = tools
        self.ainvoke = AsyncMock(return_value=self.__class__.next_result)
        _FakeToolNode.last_instance = self


class _FakeToolMessage:
    """Fake LangChain ToolMessage for testing."""

    def __init__(self, *, content: str = "", tool_call_id: str = "") -> None:
        self.content = content
        self.tool_call_id = tool_call_id


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
async def test_tools_node_builds_tool_message_through_message_adapter() -> None:
    from dataclasses import replace

    raw_tool = MagicMock()
    raw_tool.name = "file_read"
    runner = _runner(raw_tool)
    state = runner.build_initial_state("inspect")
    state["steps_executed"] = 1
    state["messages"] = [
        {"role": "system", "content": "system prompt"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-2",
                    "type": "function",
                    "function": {"name": "file_read", "arguments": '{"file_path": "x.txt"}'},
                }
            ],
        },
    ]
    _FakeToolNode.next_result = {
        "messages": [_FakeToolMessage(content="adapter-output", tool_call_id="call-2")]
    }

    captured = {}

    def fake_to_langchain_list(messages):
        captured["to_langchain"] = messages
        return [SimpleNamespace(payload=messages)]

    def fake_to_agent_list(messages):
        captured["to_agent"] = messages
        return [
            {
                "role": "tool",
                "tool_call_id": "call-2",
                "content": "adapter-output",
            }
        ]

    adapted_tool = object()
    deps = runner._deps
    runner._deps = replace(
        deps,
        adapt_tools=MagicMock(return_value=[adapted_tool]),
        agent_messages_to_langchain_messages=fake_to_langchain_list,
        langchain_messages_to_agent_dicts=fake_to_agent_list,
    )
    updated = await runner.tools_node(state)

    assert _FakeToolNode.last_instance is not None
    _FakeToolNode.last_instance.ainvoke.assert_awaited_once()
    assert "to_langchain" in captured
    assert "to_agent" in captured
    assert updated["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "call-2",
        "content": "adapter-output",
    }
    assert updated["tool_calls_executed"] == 1


@pytest.mark.asyncio
async def test_tools_node_returns_unknown_tool_error_without_invoking_tool_node() -> None:
    raw_tool = MagicMock()
    raw_tool.name = "file_read"
    _FakeToolNode.last_instance = None
    runner = _runner(raw_tool)
    state = runner.build_initial_state("inspect")
    state["steps_executed"] = 1
    state["messages"] = [
        {"role": "system", "content": "system prompt"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-unknown",
                    "type": "function",
                    "function": {"name": "missing_tool", "arguments": "{}"},
                }
            ],
        },
    ]

    with patch(
        "beep.agent.graph_runtime_deps_factory.tool_result_to_langchain_message",
        side_effect=lambda *, tool_call_id, content: SimpleNamespace(
            tool_call_id=tool_call_id,
            content=content,
        ),
    ):
        with patch(
            "beep.agent.graph_runtime_deps_factory.langchain_message_to_agent_dict",
            side_effect=lambda message: {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content,
            },
        ):
            updated = await runner.tools_node(state)

    assert updated["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "call-unknown",
        "content": "Unknown tool: missing_tool",
    }
    assert (
        _FakeToolNode.last_instance is None or _FakeToolNode.last_instance.ainvoke.await_count == 0
    )
