"""Batch tool calls for parallel execution.

Groups consecutive read-only tool calls into batches while keeping
write tools isolated as single-item batches to prevent conflicts.
"""

from __future__ import annotations

from typing import Any

from beep.agent.parallel.classifier import is_read_only_tool


def batch_tool_calls(
    tool_calls: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Group tool calls into parallel-safe batches.

    Strategy:
    - Consecutive read-only tools are grouped into one batch
    - Write tools always get their own single-item batch
    - Order is preserved

    Example:
        [read, read, write, read, read, write]
        → [[read, read], [write], [read, read], [write]]

    Args:
        tool_calls: List of tool call dicts with 'function.name' field

    Returns:
        List of batches, each batch is a list of tool calls
    """
    if not tool_calls:
        return []

    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_is_read = True

    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        tool_name = str(function.get("name", ""))
        is_read = is_read_only_tool(tool_name)

        if current_batch and is_read != current_is_read:
            batches.append(current_batch)
            current_batch = []

        current_batch.append(tool_call)
        current_is_read = is_read

    if current_batch:
        batches.append(current_batch)

    return batches
