"""Tool call limit enforcement for the agent graph runner.

Each function returns True when the limit is hit so the caller
can break out of the tool-execution loop.
"""

from __future__ import annotations

from typing import Any

from beep.agent.graph_support import AgentGraphState


def check_per_step_limit(
    runner: Any,
    state: AgentGraphState,
    tool_calls: list[dict[str, Any]],
    tool_index: int,
    tool_messages_by_id: dict[str, dict[str, Any]],
    step: int,
) -> bool:
    if tool_index < runner._max_tool_calls_per_step:
        return False
    state["per_step_limit_hit"] = True
    runner._deps.console.print(
        f"[yellow]Tool call limit reached ({runner._max_tool_calls_per_step}) "
        "for this step; skipping remaining tool calls.[/yellow]"
    )
    runner._deps.log_event(
        "agent.tool.limit_reached",
        step=step,
        limit=runner._max_tool_calls_per_step,
        total=len(tool_calls),
    )
    for remaining in tool_calls[tool_index:]:
        rid = str(remaining.get("id", ""))
        tool_messages_by_id[rid] = runner._build_tool_message(
            tool_call_id=rid,
            content=f"Skipped: per-step tool call limit ({runner._max_tool_calls_per_step}) reached.",
        )
    return True


def check_total_limit(
    runner: Any,
    state: AgentGraphState,
    tool_calls: list[dict[str, Any]],
    tool_index: int,
    tool_messages_by_id: dict[str, dict[str, Any]],
    step: int,
) -> bool:
    if state["tool_calls_executed"] < runner._max_tool_calls_total:
        return False
    state["total_limit_hit"] = True
    runner._deps.console.print(
        f"[yellow]Total tool call limit reached ({runner._max_tool_calls_total}); "
        "stopping agent run.[/yellow]"
    )
    runner._deps.log_event(
        "agent.tool.total_limit_reached",
        step=step,
        limit=runner._max_tool_calls_total,
        executed=state["tool_calls_executed"],
    )
    for remaining in tool_calls[tool_index:]:
        rid = str(remaining.get("id", ""))
        tool_messages_by_id[rid] = runner._build_tool_message(
            tool_call_id=rid,
            content=f"Skipped: total tool call limit ({runner._max_tool_calls_total}) reached.",
        )
    return True


def check_repeated_calls(
    runner: Any,
    state: AgentGraphState,
    tool_calls: list[dict[str, Any]],
    tool_index: int,
    tool_name: str,
    arguments_str: str,
    tool_messages_by_id: dict[str, dict[str, Any]],
    step: int,
) -> bool:
    call_key = f"{tool_name}:{arguments_str}"
    call_count = state["tool_call_hashes"].get(call_key, 0) + 1
    state["tool_call_hashes"][call_key] = call_count
    if call_count <= runner._max_repeated_calls:
        return False
    runner._deps.console.print(
        f"[yellow]Loop detected: '{tool_name}' called with identical arguments {call_count} times "
        f"(limit {runner._max_repeated_calls}). Stopping to avoid infinite loop.[/yellow]"
    )
    runner._deps.log_event(
        "agent.tool.repeated",
        step=step,
        tool_name=tool_name,
        count=call_count,
    )
    for remaining in tool_calls[tool_index:]:
        rid = str(remaining.get("id", ""))
        tool_messages_by_id[rid] = runner._build_tool_message(
            tool_call_id=rid,
            content=(
                f"Aborted: '{tool_name}' has been called with identical arguments {call_count} times. "
                "Try a different approach or tool."
            ),
        )
    return True
