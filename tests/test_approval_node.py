"""Tests for the LangGraph agent approval node."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
async def test_approval_node_creates_denied_tool_message_for_destructive_call() -> None:
    raw_tool = MagicMock()
    raw_tool.name = "file_write"
    runner = _runner(raw_tool, auto_approve=False)
    state = runner.build_initial_state("inspect")
    state["steps_executed"] = 1
    state["messages"] = [
        {"role": "system", "content": "system prompt"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-denied",
                    "type": "function",
                    "function": {"name": "file_write", "arguments": '{"file_path": "x.txt"}'},
                }
            ],
        },
    ]

    runner._deps = SimpleNamespace(
        **{**runner._deps.__dict__, "request_approval": lambda *_args, **_kwargs: False}
    )
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
            updated = await runner.approval_node(state)

    assert updated["pending_tool_messages"] == [
        {"role": "tool", "tool_call_id": "call-denied", "content": "User denied approval"}
    ]
    assert runner.route_after_approval(updated) == "tools"


@pytest.mark.asyncio
async def test_approval_node_skips_prompt_for_explicitly_safe_mcp_tool() -> None:
    raw_tool = MagicMock()
    raw_tool.name = "query_docs"
    raw_tool.requires_human_approval = False
    runner = _runner(raw_tool, auto_approve=False)
    state = runner.build_initial_state("inspect")
    state["steps_executed"] = 1
    state["messages"] = [
        {"role": "system", "content": "system prompt"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-safe",
                    "type": "function",
                    "function": {"name": "query_docs", "arguments": '{"query": "policy"}'},
                }
            ],
        },
    ]

    request_mock = MagicMock(return_value=False)
    runner._deps = SimpleNamespace(**{**runner._deps.__dict__, "request_approval": request_mock})
    updated = await runner.approval_node(state)

    assert updated["pending_tool_messages"] == []
    request_mock.assert_not_called()


@pytest.mark.asyncio
async def test_approval_node_blocks_policy_denied_tool_call_before_prompt() -> None:
    raw_tool = MagicMock()
    raw_tool.name = "file_write"
    runner = _runner(raw_tool, auto_approve=False, sandbox_mode=SandboxMode.READ_ONLY)
    state = runner.build_initial_state("inspect")
    state["steps_executed"] = 1
    state["messages"] = [
        {"role": "system", "content": "system prompt"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-blocked",
                    "type": "function",
                    "function": {"name": "file_write", "arguments": '{"file_path": "x.txt"}'},
                }
            ],
        },
    ]

    request_mock = MagicMock(return_value=True)
    runner._deps = SimpleNamespace(**{**runner._deps.__dict__, "request_approval": request_mock})
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
            updated = await runner.approval_node(state)

    assert len(updated["pending_tool_messages"]) == 1
    assert updated["pending_tool_messages"][0]["tool_call_id"] == "call-blocked"
    assert updated["pending_tool_messages"][0]["content"].startswith("Blocked by sandbox policy:")
    request_mock.assert_not_called()


@pytest.mark.asyncio
async def test_auto_approve_does_not_bypass_policy_blocks() -> None:
    raw_tool = MagicMock()
    raw_tool.name = "shell"
    runner = _runner(raw_tool, auto_approve=True, sandbox_mode=SandboxMode.READ_ONLY)
    state = runner.build_initial_state("inspect")
    state["steps_executed"] = 1
    state["messages"] = [
        {"role": "system", "content": "system prompt"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-shell",
                    "type": "function",
                    "function": {"name": "shell", "arguments": '{"command": "pytest"}'},
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
            updated = await runner.approval_node(state)

    assert len(updated["pending_tool_messages"]) == 1
    assert updated["pending_tool_messages"][0]["tool_call_id"] == "call-shell"
    assert updated["pending_tool_messages"][0]["content"].startswith("Blocked by sandbox policy:")
