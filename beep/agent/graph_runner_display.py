"""TODO display and run summary for the agent graph runner."""

from __future__ import annotations

from typing import Any

from beep.agent.graph_support import AgentGraphState
from beep.agent.planning import TodoList


def render_todo(todo_list: TodoList, state: AgentGraphState, console: Any) -> None:
    """Render the current TODO list as a compact progress indicator."""
    if not todo_list:
        return
    if not state.get("todo_list", {}):
        return

    from rich.table import Table

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Status", style="dim")
    table.add_column("Task")

    for item in todo_list.items:
        icon = {"pending": "○", "in_progress": "◉", "completed": "●", "cancelled": "✗"}.get(
            item.status, "○"
        )
        style = {
            "pending": "dim",
            "in_progress": "cyan",
            "completed": "green",
            "cancelled": "red",
        }.get(item.status, "dim")
        table.add_row(f"[{style}]{icon}[/{style}]", item.content)

    console.print(table)


def emit_summary(state: AgentGraphState, console: Any, log_event: Any) -> None:
    """Print and log the agent run summary."""
    summary = (
        f"steps={state['steps_executed']}, "
        f"tool_calls={state['tool_calls_executed']}, "
        f"per_step_limit_hit={state['per_step_limit_hit']}, "
        f"total_limit_hit={state['total_limit_hit']}, "
        f"reason={state['run_reason']}"
    )
    console.print(f"[dim]Run summary: {summary}[/dim]")
    log_event(
        "agent.run.summary",
        steps_executed=state["steps_executed"],
        tool_calls_executed=state["tool_calls_executed"],
        per_step_limit_hit=state["per_step_limit_hit"],
        total_limit_hit=state["total_limit_hit"],
        reason=state["run_reason"],
    )
