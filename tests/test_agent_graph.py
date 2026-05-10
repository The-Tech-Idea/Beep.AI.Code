"""Tests for LangGraph agent run and resume orchestration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.agent.graph import resume_graph, run_graph


class _FakeCompiledGraph:
    def __init__(self, result: dict[str, object]) -> None:
        self._result = result
        self.ainvoke = AsyncMock(return_value=result)


class _FakeStateGraph:
    last_instance: "_FakeStateGraph | None" = None

    def __init__(self, _state_type: object) -> None:
        self.nodes: dict[str, object] = {}
        self.edges: list[tuple[object, object]] = []
        self.conditional_edges: list[tuple[str, object, dict[str, object]]] = []
        self.compiled = _FakeCompiledGraph(
            {
                "messages": [],
                "steps_executed": 2,
                "tool_calls_executed": 1,
                "files_touched": [],
                "run_reason": "completed",
                "final_message": "done",
                "consecutive_failure_steps": 0,
                "tool_call_hashes": {},
                "per_step_limit_hit": False,
                "total_limit_hit": False,
                "pending_tool_messages": [],
            }
        )
        _FakeStateGraph.last_instance = self

    def add_node(self, name: str, node: object) -> None:
        self.nodes[name] = node

    def add_edge(self, start: object, end: object) -> None:
        self.edges.append((start, end))

    def add_conditional_edges(self, name: str, route: object, mapping: dict[str, object]) -> None:
        self.conditional_edges.append((name, route, mapping))

    def compile(self, *, checkpointer: object) -> _FakeCompiledGraph:
        self.checkpointer = checkpointer
        return self.compiled


class _FakeAsyncSqliteSaverContext:
    def __init__(self, conn_string: str, *, checkpoint_exists: bool = True) -> None:
        self.conn_string = conn_string
        self.checkpoint_exists = checkpoint_exists

    async def __aenter__(self) -> "_FakeAsyncSqliteSaverContext":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def aget_tuple(self, config: dict[str, object]) -> dict[str, object] | None:
        if not self.checkpoint_exists:
            return None
        return {"config": config}


class _FakeAsyncSqliteSaver:
    checkpoint_exists = True

    @classmethod
    def from_conn_string(cls, conn_string: str) -> _FakeAsyncSqliteSaverContext:
        return _FakeAsyncSqliteSaverContext(conn_string, checkpoint_exists=cls.checkpoint_exists)


@pytest.mark.asyncio
async def test_run_graph_builds_state_graph_and_invokes_checkpointed_run() -> None:
    backend = MagicMock()
    backend.complete = AsyncMock()
    tool = MagicMock()
    tool.name = "file_read"
    tool.to_openai_tool.return_value = {"type": "function", "function": {"name": "file_read"}}

    with patch(
        "beep.agent.graph._load_langgraph_dependencies",
        return_value=("__start__", "__end__", _FakeStateGraph, _FakeAsyncSqliteSaver, None),
    ):
        with patch("beep.agent.graph.append_message"):
            final_state = await run_graph(
                goal="inspect",
                backend=backend,
                tools=[tool],
                workspace_root=Path.cwd(),
                system_prompt="system prompt",
                workspace_rules=[],
                session_id="thread-1",
                max_steps=5,
                max_tool_calls_per_step=3,
                max_tool_calls_total=10,
                step_timeout=30.0,
                max_repeated_calls=3,
                max_consecutive_failures=2,
                max_tool_output_chars=4000,
                auto_approve=True,
            )

    assert final_state["run_reason"] == "completed"
    builder = _FakeStateGraph.last_instance
    assert builder is not None
    assert set(builder.nodes) == {"agent", "approval", "tools"}
    assert ("__start__", "agent") in builder.edges
    builder.compiled.ainvoke.assert_awaited_once()
    initial_state = builder.compiled.ainvoke.await_args.args[0]
    assert initial_state["messages"][0]["content"] == "system prompt"
    assert initial_state["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_run_graph_raises_clear_error_when_langgraph_missing() -> None:
    backend = MagicMock()
    backend.complete = AsyncMock()
    tool = MagicMock()
    tool.name = "file_read"
    tool.to_openai_tool.return_value = {"type": "function", "function": {"name": "file_read"}}

    with patch(
        "beep.agent.graph._load_langgraph_dependencies",
        side_effect=RuntimeError("LangGraph runtime packages are not installed."),
    ):
        with pytest.raises(RuntimeError, match="LangGraph runtime packages"):
            await run_graph(
                goal="inspect",
                backend=backend,
                tools=[tool],
                workspace_root=Path.cwd(),
                system_prompt="system prompt",
                workspace_rules=[],
                session_id="thread-2",
                max_steps=5,
                max_tool_calls_per_step=3,
                max_tool_calls_total=10,
                step_timeout=30.0,
                max_repeated_calls=3,
                max_consecutive_failures=2,
                max_tool_output_chars=4000,
                auto_approve=True,
            )


@pytest.mark.asyncio
async def test_run_graph_builds_multimodal_initial_user_message() -> None:
    backend = MagicMock()
    backend.complete = AsyncMock()
    tool = MagicMock()
    tool.name = "file_read"
    tool.to_openai_tool.return_value = {"type": "function", "function": {"name": "file_read"}}
    initial_user_content = [
        {"type": "text", "text": "Extract only the failing test names."},
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,AAAA"},
        },
    ]

    with patch(
        "beep.agent.graph._load_langgraph_dependencies",
        return_value=("__start__", "__end__", _FakeStateGraph, _FakeAsyncSqliteSaver, None),
    ):
        with patch("beep.agent.graph.append_message") as append_message_mock:
            await run_graph(
                goal="inspect screenshot",
                initial_user_content=initial_user_content,
                backend=backend,
                tools=[tool],
                workspace_root=Path.cwd(),
                system_prompt="system prompt",
                workspace_rules=[],
                session_id="thread-mm",
                max_steps=5,
                max_tool_calls_per_step=3,
                max_tool_calls_total=10,
                step_timeout=30.0,
                max_repeated_calls=3,
                max_consecutive_failures=2,
                max_tool_output_chars=4000,
                auto_approve=True,
            )

    builder = _FakeStateGraph.last_instance
    assert builder is not None
    initial_state = builder.compiled.ainvoke.await_args.args[0]
    user_message = initial_state["messages"][1]
    assert isinstance(user_message["content"], list)
    assert user_message["content"][0]["type"] == "text"
    assert "Achieve this goal: inspect screenshot" in user_message["content"][0]["text"]
    assert user_message["content"][1:] == initial_user_content
    user_history_calls = [
        call.args[1]
        for call in append_message_mock.call_args_list
        if call.args[1].get("role") == "user"
    ]
    assert len(user_history_calls) == 1
    assert user_history_calls[0]["content"] == user_message["content"]


@pytest.mark.asyncio
async def test_resume_graph_uses_existing_thread_checkpoint() -> None:
    backend = MagicMock()
    backend.complete = AsyncMock()
    tool = MagicMock()
    tool.name = "file_read"
    tool.to_openai_tool.return_value = {"type": "function", "function": {"name": "file_read"}}
    _FakeAsyncSqliteSaver.checkpoint_exists = True

    with patch(
        "beep.agent.graph._load_langgraph_dependencies",
        return_value=("__start__", "__end__", _FakeStateGraph, _FakeAsyncSqliteSaver, None),
    ):
        with patch("beep.agent.graph.append_message"):
            final_state = await resume_graph(
                backend=backend,
                tools=[tool],
                workspace_root=Path.cwd(),
                system_prompt="system prompt",
                workspace_rules=[],
                session_id="thread-1",
                max_steps=5,
                max_tool_calls_per_step=3,
                max_tool_calls_total=10,
                step_timeout=30.0,
                max_repeated_calls=3,
                max_consecutive_failures=2,
                max_tool_output_chars=4000,
                auto_approve=True,
            )

    assert final_state["run_reason"] == "completed"
    builder = _FakeStateGraph.last_instance
    assert builder is not None
    builder.compiled.ainvoke.assert_awaited_once_with(
        None,
        config={"configurable": {"thread_id": "thread-1"}},
    )


@pytest.mark.asyncio
async def test_resume_graph_raises_for_missing_checkpoint() -> None:
    backend = MagicMock()
    backend.complete = AsyncMock()
    tool = MagicMock()
    tool.name = "file_read"
    tool.to_openai_tool.return_value = {"type": "function", "function": {"name": "file_read"}}
    _FakeAsyncSqliteSaver.checkpoint_exists = False

    with patch(
        "beep.agent.graph._load_langgraph_dependencies",
        return_value=("__start__", "__end__", _FakeStateGraph, _FakeAsyncSqliteSaver, None),
    ):
        with pytest.raises(RuntimeError, match="No checkpointed agent thread found"):
            await resume_graph(
                backend=backend,
                tools=[tool],
                workspace_root=Path.cwd(),
                system_prompt="system prompt",
                workspace_rules=[],
                session_id="missing-thread",
                max_steps=5,
                max_tool_calls_per_step=3,
                max_tool_calls_total=10,
                step_timeout=30.0,
                max_repeated_calls=3,
                max_consecutive_failures=2,
                max_tool_output_chars=4000,
                auto_approve=True,
            )
