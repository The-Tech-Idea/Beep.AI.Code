"""Execution entrypoints for the LangGraph-backed autonomous agent runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from rich.panel import Panel

from beep.agent.backends import AgentModelBackend
from beep.agent.graph_runner import AgentGraphRunner, InitialUserContent
from beep.agent.graph_support import AgentGraphState, _build_compiled_graph, _checkpoint_path
from beep.agent.planning import TodoList
from beep.utils.console import get_console
from beep.agent.tools.base import BaseTool
from beep.permissions.manager import SandboxMode
from beep.rules.loader import LoadedRule
from beep.utils.json_logging import log_event


def _build_runner(
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
    sandbox_mode: SandboxMode | str,
    tool_node_cls: Any | None,
    todo_list: TodoList | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
    provider_options: dict[str, Any] | None = None,
) -> AgentGraphRunner:
    runner = AgentGraphRunner(
        backend=backend,
        tools=tools,
        workspace_root=workspace_root,
        max_steps=max_steps,
        max_tool_calls_per_step=max_tool_calls_per_step,
        max_tool_calls_total=max_tool_calls_total,
        step_timeout=step_timeout,
        max_repeated_calls=max_repeated_calls,
        max_consecutive_failures=max_consecutive_failures,
        max_tool_output_chars=max_tool_output_chars,
        auto_approve=auto_approve,
        sandbox_mode=sandbox_mode,
        system_prompt=system_prompt,
        workspace_rules=workspace_rules,
        session_id=session_id,
        tool_node_cls=tool_node_cls,
        todo_list=todo_list,
        auto_verify=auto_verify,
    )
    runner.set_provider_options(provider_options)
    runner.set_response_format(response_format)
    return runner


async def run_graph_impl(
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
    sandbox_mode: SandboxMode | str,
    load_langgraph_dependencies: Callable[[], tuple[Any, Any, Any, Any, Any]],
    append_message_fn: Callable[[str, dict[str, Any]], Any],
    todo_list: TodoList | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
    provider_options: dict[str, Any] | None = None,
) -> AgentGraphState:
    get_console().print(Panel(f"[bold]{goal}[/bold]", title="Agent Goal", border_style="blue"))
    log_event("agent.run.start", goal=goal, max_steps=max_steps, tool_count=len(tools))

    start, end, state_graph_cls, async_sqlite_saver_cls, tool_node_cls = (
        load_langgraph_dependencies()
    )
    todo_list = todo_list or TodoList()
    runner = _build_runner(
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
        response_format=response_format,
        provider_options=provider_options,
    )

    checkpoint_path = _checkpoint_path(workspace_root)
    append_message_fn(
        session_id,
        runner.build_initial_user_message(goal, initial_user_content=initial_user_content),
    )
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
        final_state = await graph.ainvoke(initial_state, config=config)

    log_event(
        "agent.run.done", steps=final_state["steps_executed"], reason=final_state["run_reason"]
    )
    runner.emit_summary(final_state)
    append_message_fn(
        session_id,
        {
            "role": "meta",
            "reason": final_state["run_reason"],
            "steps": final_state["steps_executed"],
        },
    )
    return final_state


async def resume_graph_impl(
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
    sandbox_mode: SandboxMode | str,
    load_langgraph_dependencies: Callable[[], tuple[Any, Any, Any, Any, Any]],
    append_message_fn: Callable[[str, dict[str, Any]], Any],
    todo_list: TodoList | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
    provider_options: dict[str, Any] | None = None,
) -> AgentGraphState:
    get_console().print(
        Panel(f"[bold]{session_id}[/bold]", title="Resuming Agent Thread", border_style="blue")
    )
    log_event(
        "agent.run.resume.start",
        session_id=session_id,
        max_steps=max_steps,
        tool_count=len(tools),
    )

    start, end, state_graph_cls, async_sqlite_saver_cls, tool_node_cls = (
        load_langgraph_dependencies()
    )
    todo_list = todo_list or TodoList()
    runner = _build_runner(
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
        response_format=response_format,
        provider_options=provider_options,
    )

    checkpoint_path = _checkpoint_path(workspace_root)
    config = {"configurable": {"thread_id": session_id}}
    async with async_sqlite_saver_cls.from_conn_string(str(checkpoint_path)) as checkpointer:
        checkpoint = await checkpointer.aget_tuple(config)
        if checkpoint is None:
            raise RuntimeError(f'No checkpointed agent thread found for "{session_id}".')
        graph = _build_compiled_graph(
            state_graph_cls=state_graph_cls,
            start=start,
            end=end,
            runner=runner,
            checkpointer=checkpointer,
        )
        final_state = await graph.ainvoke(None, config=config)

    log_event(
        "agent.run.resume.done",
        session_id=session_id,
        steps=final_state["steps_executed"],
        reason=final_state["run_reason"],
    )
    runner.emit_summary(final_state)
    append_message_fn(
        session_id,
        {
            "role": "meta",
            "reason": final_state["run_reason"],
            "steps": final_state["steps_executed"],
        },
    )
    return final_state
