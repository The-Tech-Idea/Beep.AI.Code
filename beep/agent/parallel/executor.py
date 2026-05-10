"""Parallel tool call executor.

Executes batches of tool calls concurrently for read-only tools
and sequentially for write tools.
"""

from __future__ import annotations

import asyncio
from typing import Any

from beep.agent.parallel.batcher import batch_tool_calls
from beep.agent.parallel.classifier import is_read_only_tool

DEFAULT_MAX_CONCURRENCY = 5


async def _execute_read_batch(
    batch: list[dict[str, Any]],
    tool_node: Any,
    messages: list[Any],
    max_concurrency: int,
) -> list[Any]:
    """Execute a batch of read-only tool calls concurrently."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _call_with_semaphore(tool_call: dict[str, Any]) -> Any:
        async with semaphore:
            single_messages = [*messages[:-1], {**messages[-1], "tool_calls": [tool_call]}]
            result = await tool_node.ainvoke({"messages": single_messages})
            return result.get("messages", []) if isinstance(result, dict) else []

    tasks = [_call_with_semaphore(tc) for tc in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: list[Any] = []
    for result in results:
        if isinstance(result, Exception):
            merged.append({"error": str(result)})
        elif isinstance(result, list):
            merged.extend(result)
    return merged


async def _execute_write_sequential(
    batch: list[dict[str, Any]],
    tool_node: Any,
    messages: list[Any],
) -> list[Any]:
    """Execute write tool calls sequentially."""
    all_results: list[Any] = []
    for tool_call in batch:
        single_messages = [*messages[:-1], {**messages[-1], "tool_calls": [tool_call]}]
        result = await tool_node.ainvoke({"messages": single_messages})
        if isinstance(result, dict):
            all_results.extend(result.get("messages", []))
    return all_results


async def execute_parallel_batch(
    tool_calls: list[dict[str, Any]],
    tool_node: Any,
    messages: list[Any],
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
) -> list[Any]:
    """Execute tool calls with parallel read and sequential write.

    Reads the full message list, batches tool calls, and executes
    each batch according to its type (parallel for reads, sequential for writes).

    Args:
        tool_calls: List of tool call dicts
        tool_node: LangGraph ToolNode instance
        messages: Full LangChain message list
        max_concurrency: Max concurrent read operations

    Returns:
        Flattened list of tool result messages
    """
    if not tool_calls:
        return []

    batches = batch_tool_calls(tool_calls)
    all_results: list[Any] = []

    for batch in batches:
        if not batch:
            continue
        function = batch[0].get("function", {})
        tool_name = str(function.get("name", ""))
        is_read = is_read_only_tool(tool_name)

        if is_read:
            results = await _execute_read_batch(batch, tool_node, messages, max_concurrency)
        else:
            results = await _execute_write_sequential(batch, tool_node, messages)

        all_results.extend(results)

    return all_results
