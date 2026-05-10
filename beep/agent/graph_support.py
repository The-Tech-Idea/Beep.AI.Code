"""Shared support utilities for the LangGraph-backed agent runtime."""

from __future__ import annotations

import operator
from pathlib import Path
from typing import Annotated, Any, TypedDict

from rich.panel import Panel

from beep.agent.tools.base import ToolResult


from beep.utils.console import get_console

_FILE_TOUCH_TOOLS: frozenset[str] = frozenset(
    {"file_edit", "single_edit", "file_write", "project_scaffold"}
)

_STATE_SCHEMA_VERSION = "2.0"


class AgentGraphState(TypedDict):
    """Serializable state tracked by the LangGraph runtime.

    Uses Annotated reducers to prevent silent data loss on parallel branches
    and checkpoint resume. Accumulator fields (messages, files_touched, recent_errors,
    pending_tool_messages) use list-append reducers; overwrite fields use plain types.
    """

    schema_version: str
    messages: Annotated[list[dict[str, Any]], operator.add]
    steps_executed: int
    tool_calls_executed: int
    files_touched: Annotated[list[str], operator.add]
    run_reason: str | None
    final_message: str | None
    consecutive_failure_steps: int
    tool_call_hashes: dict[str, int]
    per_step_limit_hit: bool
    total_limit_hit: bool
    pending_tool_messages: Annotated[list[dict[str, Any]], operator.add]
    recent_errors: Annotated[list[dict[str, Any]], operator.add]
    max_retries: int
    error_count: int
    todo_list: dict[str, dict[str, str]]


def _checkpoint_path(workspace_root: Path) -> Path:
    checkpoint_dir = workspace_root / ".beep"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir / "agent_state.sqlite"


def _build_compiled_graph(
    *,
    state_graph_cls: Any,
    start: Any,
    end: Any,
    runner: Any,
    checkpointer: Any,
) -> Any:
    graph_builder = state_graph_cls(AgentGraphState)
    graph_builder.add_node("agent", runner.agent_node)
    graph_builder.add_node("approval", runner.approval_node)
    graph_builder.add_node("tools", runner.tools_node)
    graph_builder.add_edge(start, "agent")
    graph_builder.add_conditional_edges(
        "agent",
        runner.route_after_agent,
        {"approval": "approval", "__end__": end},
    )
    graph_builder.add_conditional_edges(
        "approval",
        runner.route_after_approval,
        {"tools": "tools", "__end__": end},
    )
    graph_builder.add_conditional_edges(
        "tools",
        runner.route_after_tools,
        {"agent": "agent", "__end__": end},
    )
    return graph_builder.compile(checkpointer=checkpointer)


def _load_langgraph_dependencies() -> tuple[Any, Any, Any, Any, Any]:
    """Import LangGraph lazily so the main CLI env does not require it."""
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        from langgraph.graph import END, START, StateGraph
        from langgraph.prebuilt import ToolNode
    except ImportError as exc:
        raise RuntimeError(
            'LangGraph runtime packages are not installed. Run "beep agent setup" to provision the managed agent environment.'
        ) from exc
    return START, END, StateGraph, AsyncSqliteSaver, ToolNode


def _format_tool_result(tool_name: str, result: ToolResult, step: int) -> None:
    border = "green" if result.success else "red"
    status = "OK" if result.success else "FAILED"

    content = result.output or ""
    if result.error:
        content += f"\nError: {result.error}"

    get_console().print(
        Panel(
            content[:500] + ("..." if len(content) > 500 else ""),
            title=f"Step {step}: {tool_name} ({status})",
            border_style=border,
            padding=(1, 2),
        )
    )
