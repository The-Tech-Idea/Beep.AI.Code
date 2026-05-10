"""Tests for the LangGraph agent node."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.agent.graph import AgentGraphRunner
from beep.agent.streaming import StreamEmitter
from beep.permissions.manager import SandboxMode
from beep.api.streaming import CompletionStreamDelta, ToolCallDelta


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
    with patch(
        "beep.agent.graph_runner._attach_tool_approval_policies",
        side_effect=lambda deps, tools, workspace_root, sandbox_mode: deps,
    ):
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
async def test_agent_node_normalizes_assistant_message_through_message_adapter() -> None:
    from beep.agent.message_adapter import AgentCompletion

    raw_tool = MagicMock()
    raw_tool.name = "file_read"
    runner = _runner(raw_tool)
    state = runner.build_initial_state("inspect")
    state["messages"] = [{"role": "system", "content": "system prompt"}]
    runner._backend.complete = AsyncMock(
        return_value=AgentCompletion(
            content="thinking",
            tool_calls=[
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "file_read", "arguments": "{}"},
                }
            ],
        )
    )

    captured = {}

    def fake_to_langchain(message):
        captured["to_langchain"] = message
        return SimpleNamespace(payload=message)

    def fake_to_agent(message):
        captured["to_agent"] = message
        return {**message.payload, "content": "normalized"}

    deps = runner._deps
    runner._deps = replace(
        deps,
        agent_dict_to_langchain_message=fake_to_langchain,
        langchain_message_to_agent_dict=fake_to_agent,
    )
    with patch("beep.agent.graph_runtime_deps_factory.render_response"):
        updated = await runner.agent_node(state)

    assert "to_langchain" in captured
    assert captured["to_langchain"] == {
        "role": "assistant",
        "content": "thinking",
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": "file_read", "arguments": "{}"},
            }
        ],
    }
    assert "to_agent" in captured
    assert updated["messages"][-1]["content"] == "normalized"


@pytest.mark.asyncio
async def test_agent_node_streams_deltas_through_emitter_and_forwards_provider_options() -> None:
    raw_tool = MagicMock()
    raw_tool.name = "file_read"
    runner = _runner(raw_tool)
    runner.set_stream_emitter(StreamEmitter())
    runner.set_provider_options({"parallel_tool_calls": False})
    state = runner.build_initial_state("inspect")
    state["messages"] = [{"role": "system", "content": "system prompt"}]

    captured_request = {}

    deps = runner._deps
    runner._deps = replace(
        deps,
        agent_dict_to_langchain_message=lambda message: SimpleNamespace(payload=message),
        langchain_message_to_agent_dict=lambda message: message.payload,
    )

    async def fake_stream_request(backend, request):
        del backend
        captured_request["request"] = request
        yield CompletionStreamDelta(content="Thinking")
        yield CompletionStreamDelta(
            tool_calls=(
                ToolCallDelta(
                    index=0,
                    id="call-1",
                    name="file_read",
                    arguments="{}",
                ),
            )
        )

    with (
        patch("beep.agent.graph_runner_steps.stream_agent_completion_request", fake_stream_request),
        patch("beep.agent.graph_runtime_deps_factory.render_response") as render_response,
    ):
        updated = await runner.agent_node(state)

    request = captured_request["request"]
    assert request.stream is True
    assert request.provider_options == {"parallel_tool_calls": False}
    assert updated["messages"][-1]["tool_calls"][0]["function"]["name"] == "file_read"
    assert [event.type for event in runner._stream_emitter.history] == ["response_chunk", "tool_start"]
    render_response.assert_not_called()
