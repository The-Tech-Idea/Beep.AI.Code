"""LangGraph-backed execution runtime for the autonomous coding agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator

from beep.agent.backends import AgentModelBackend
from beep.agent.graph_execution import resume_graph_impl, run_graph_impl
from beep.agent.graph_interrupt import build_interrupt_graph, get_interrupt_payload, is_interrupted
from beep.agent.graph_runner import AgentGraphRunner as _AgentGraphRunner, InitialUserContent
from beep.agent.graph_runtime_deps_factory import make_graph_runtime_dependencies
from beep.agent.graph_streaming import stream_graph_events
from beep.agent.graph_support import (
    AgentGraphState,
    _build_compiled_graph,
    _checkpoint_path,
    _load_langgraph_dependencies,
)
from beep.agent.planning import TodoList
from beep.agent.streaming import StreamEmitter
from beep.agent.tools.base import BaseTool
from beep.permissions.manager import SandboxMode
from beep.rules.loader import LoadedRule
from beep.sessions.history import append_message
from beep.utils.json_logging import log_event


class AgentGraphRunner(_AgentGraphRunner):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("runtime_deps", make_graph_runtime_dependencies())
        super().__init__(*args, **kwargs)


async def run_graph(
    *,
    goal: str,
    initial_user_content: InitialUserContent | None = None,
    backend: AgentModelBackend,
    tools: list[BaseTool],
    workspace_root: Path,
    system_prompt: str,
    workspace_rules: list[LoadedRule] | None,
    session_id: str,
    max_steps: int,
    max_tool_calls_per_step: int,
    max_tool_calls_total: int,
    step_timeout: float,
    max_repeated_calls: int,
    max_consecutive_failures: int,
    max_tool_output_chars: int,
    auto_approve: bool,
    sandbox_mode: SandboxMode | str = SandboxMode.WORKSPACE_WRITE,
    todo_list: TodoList | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
    provider_options: dict[str, Any] | None = None,
) -> AgentGraphState:
    return await run_graph_impl(
        goal=goal,
        initial_user_content=initial_user_content,
        backend=backend,
        tools=tools,
        workspace_root=workspace_root,
        system_prompt=system_prompt,
        workspace_rules=workspace_rules,
        session_id=session_id,
        max_steps=max_steps,
        max_tool_calls_per_step=max_tool_calls_per_step,
        max_tool_calls_total=max_tool_calls_total,
        step_timeout=step_timeout,
        max_repeated_calls=max_repeated_calls,
        max_consecutive_failures=max_consecutive_failures,
        max_tool_output_chars=max_tool_output_chars,
        auto_approve=auto_approve,
        sandbox_mode=sandbox_mode,
        load_langgraph_dependencies=_load_langgraph_dependencies,
        append_message_fn=append_message,
        todo_list=todo_list,
        auto_verify=auto_verify,
        response_format=response_format,
        provider_options=provider_options,
    )


async def resume_graph(
    *,
    backend: AgentModelBackend,
    tools: list[BaseTool],
    workspace_root: Path,
    system_prompt: str,
    workspace_rules: list[LoadedRule] | None,
    session_id: str,
    max_steps: int,
    max_tool_calls_per_step: int,
    max_tool_calls_total: int,
    step_timeout: float,
    max_repeated_calls: int,
    max_consecutive_failures: int,
    max_tool_output_chars: int,
    auto_approve: bool,
    sandbox_mode: SandboxMode | str = SandboxMode.WORKSPACE_WRITE,
    todo_list: TodoList | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
    provider_options: dict[str, Any] | None = None,
) -> AgentGraphState:
    return await resume_graph_impl(
        backend=backend,
        tools=tools,
        workspace_root=workspace_root,
        system_prompt=system_prompt,
        workspace_rules=workspace_rules,
        session_id=session_id,
        max_steps=max_steps,
        max_tool_calls_per_step=max_tool_calls_per_step,
        max_tool_calls_total=max_tool_calls_total,
        step_timeout=step_timeout,
        max_repeated_calls=max_repeated_calls,
        max_consecutive_failures=max_consecutive_failures,
        max_tool_output_chars=max_tool_output_chars,
        auto_approve=auto_approve,
        sandbox_mode=sandbox_mode,
        load_langgraph_dependencies=_load_langgraph_dependencies,
        append_message_fn=append_message,
        todo_list=todo_list,
        auto_verify=auto_verify,
        response_format=response_format,
        provider_options=provider_options,
    )


async def run_graph_streaming(
    *,
    goal: str,
    initial_user_content: InitialUserContent | None = None,
    backend: AgentModelBackend,
    tools: list[BaseTool],
    workspace_root: Path,
    system_prompt: str,
    workspace_rules: list[LoadedRule] | None,
    session_id: str,
    max_steps: int,
    max_tool_calls_per_step: int,
    max_tool_calls_total: int,
    step_timeout: float,
    max_repeated_calls: int,
    max_consecutive_failures: int,
    max_tool_output_chars: int,
    auto_approve: bool,
    sandbox_mode: SandboxMode | str = SandboxMode.WORKSPACE_WRITE,
    todo_list: TodoList | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
    provider_options: dict[str, Any] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Run the agent with streaming event output for real-time TUI feedback.

    Yields event dicts:
    - {"type": "node_start", "node": "agent", "step": 1}
    - {"type": "tool_start", "tool": "file_read", "input": {...}}
    - {"type": "tool_end", "tool": "file_read", "output": "..."}
    - {"type": "response_chunk", "content": "..."}
    - {"type": "complete", "state": {...}}
    """
    log_event("agent.run.start", goal=goal, max_steps=max_steps, tool_count=len(tools))

    start, end, state_graph_cls, async_sqlite_saver_cls, tool_node_cls = (
        _load_langgraph_dependencies()
    )
    runner = AgentGraphRunner(
        backend=backend,
        tools=tools,
        workspace_root=workspace_root,
        system_prompt=system_prompt,
        workspace_rules=workspace_rules,
        session_id=session_id,
        max_steps=max_steps,
        max_tool_calls_per_step=max_tool_calls_per_step,
        max_tool_calls_total=max_tool_calls_total,
        step_timeout=step_timeout,
        max_repeated_calls=max_repeated_calls,
        max_consecutive_failures=max_consecutive_failures,
        max_tool_output_chars=max_tool_output_chars,
        auto_approve=auto_approve,
        sandbox_mode=sandbox_mode,
        tool_node_cls=tool_node_cls,
        todo_list=todo_list,
        auto_verify=auto_verify,
    )
    emitter = StreamEmitter()
    runner.set_provider_options(provider_options)
    runner.set_response_format(response_format)
    runner.set_stream_emitter(emitter)
    append_message(
        session_id,
        runner.build_initial_user_message(goal, initial_user_content=initial_user_content),
    )

    checkpoint_path = _checkpoint_path(workspace_root)
    initial_state = runner.build_initial_state(goal, initial_user_content=initial_user_content)
    config = {"configurable": {"thread_id": session_id}}

    async with async_sqlite_saver_cls.from_conn_string(str(checkpoint_path)) as checkpointer:
        graph = _build_compiled_graph(
            state_graph_cls=state_graph_cls,
            start=start,
            end=end,
            runner=runner,
            checkpointer=checkpointer,
        )
        async for event in stream_graph_events(graph, initial_state, config, emitter=emitter):
            yield event


__all__ = [
    "AgentGraphRunner",
    "AgentGraphState",
    "_build_compiled_graph",
    "_checkpoint_path",
    "_load_langgraph_dependencies",
    "resume_graph",
    "run_graph",
    "run_graph_streaming",
    "build_interrupt_graph",
    "get_interrupt_payload",
    "is_interrupted",
]
