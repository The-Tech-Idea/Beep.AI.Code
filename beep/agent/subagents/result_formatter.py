"""Format sub-agent results for injection into parent context."""

from __future__ import annotations

from typing import Any

MAX_SUMMARY_CHARS = 500


def format_subagent_result(
    *,
    name: str,
    goal: str,
    steps_executed: int,
    final_message: str | None,
    todo_list: dict[str, Any] | None,
) -> str:
    """Produce a concise summary of a sub-agent run.

    The summary is injected as a tool result into the parent agent's
    context, so it must be short and focused.

    Args:
        name: Sub-agent type (explore, plan, etc.)
        goal: The goal the sub-agent was given
        steps_executed: Number of steps the sub-agent ran
        final_message: The sub-agent's final message
        todo_list: Serialized TODO list from the sub-agent

    Returns:
        Summary string < 500 chars
    """
    lines = [f"[{name.upper()} SUB-AGENT] Goal: {goal}"]
    lines.append(f"Steps executed: {steps_executed}")

    if todo_list:
        completed = sum(
            1
            for item in todo_list.values()
            if isinstance(item, dict) and item.get("status") == "completed"
        )
        total = len(todo_list)
        lines.append(f"Tasks completed: {completed}/{total}")

    if final_message:
        truncated = final_message[: MAX_SUMMARY_CHARS - 200]
        if len(final_message) > MAX_SUMMARY_CHARS - 200:
            truncated += "..."
        lines.append(f"\nFindings:\n{truncated}")

    summary = "\n".join(lines)
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[: MAX_SUMMARY_CHARS - 3] + "..."
    return summary
