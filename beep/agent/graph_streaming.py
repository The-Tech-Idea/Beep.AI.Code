"""Streaming support for the LangGraph agent runtime.

Provides streaming of agent responses and tool execution events
via LangGraph's astream API for real-time TUI feedback.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import asdict, is_dataclass
from typing import Any, AsyncIterator


def _event_to_dict(event: Any) -> dict[str, Any]:
    if is_dataclass(event):
        return asdict(event)
    if isinstance(event, dict):
        return event
    return {"type": "unknown", "value": event}


def _graph_update_events(
    event: dict[str, Any],
    step: int,
    *,
    include_assistant_message_events: bool,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for node_name, node_output in event.items():
        if not isinstance(node_output, dict):
            continue

        run_reason = node_output.get("run_reason")
        if run_reason:
            events.append(
                {
                    "type": "complete",
                    "node": node_name,
                    "reason": run_reason,
                    "step": step,
                    "state": node_output,
                }
            )
            continue

        messages = node_output.get("messages", [])
        if include_assistant_message_events and messages:
            last_msg = messages[-1] if isinstance(messages, list) else messages
            if isinstance(last_msg, dict):
                role = last_msg.get("role", "")
                if role == "assistant":
                    content = last_msg.get("content", "")
                    tool_calls = last_msg.get("tool_calls", [])
                    if tool_calls:
                        for tc in tool_calls:
                            fn = tc.get("function", {})
                            events.append(
                                {
                                    "type": "tool_start",
                                    "tool": fn.get("name", ""),
                                    "input": fn.get("arguments", "{}"),
                                    "step": step,
                                }
                            )
                    elif content:
                        events.append(
                            {
                                "type": "response_chunk",
                                "content": content,
                                "step": step,
                            }
                        )
                elif role == "tool":
                    tool_call_id = last_msg.get("tool_call_id", "")
                    content = last_msg.get("content", "")
                    events.append(
                        {
                            "type": "tool_end",
                            "tool_call_id": tool_call_id,
                            "output": content[:500] if content else "",
                            "step": step,
                        }
                    )

        pending = node_output.get("pending_tool_messages", [])
        if pending:
            for pm in pending:
                content = pm.get("content", "")
                if "Blocked by sandbox" in content:
                    events.append(
                        {
                            "type": "policy_denied",
                            "message": content,
                            "step": step,
                        }
                    )
                elif "denied approval" in content.lower():
                    events.append(
                        {
                            "type": "approval_denied",
                            "message": content,
                            "step": step,
                        }
                    )

        events.append(
            {
                "type": "node_end",
                "node": node_name,
                "output": node_output,
                "step": step,
            }
        )
    return events


async def stream_graph_events(
    compiled_graph: Any,
    initial_state: dict[str, Any],
    config: dict[str, Any],
    *,
    emitter: Any | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream events from graph execution for real-time feedback.

    Yields structured events:
    - {"type": "node_start", "node": "agent", "step": 1}
    - {"type": "node_end", "node": "agent", "content": "..."}
    - {"type": "tool_start", "tool": "file_read", "input": {...}}
    - {"type": "tool_end", "tool": "file_read", "output": "..."}
    - {"type": "interrupt", "payload": {...}}
    - {"type": "complete", "state": {...}}

    Args:
        compiled_graph: Compiled LangGraph graph
        initial_state: Initial agent state
        config: LangGraph config with thread_id

    Yields:
        Event dicts for each state transition
    """
    if emitter is None:
        step = 0
        async for event in compiled_graph.astream(
            initial_state,
            config=config,
            stream_mode="updates",
        ):
            step += 1
            for item in _graph_update_events(event, step, include_assistant_message_events=True):
                yield item
        return

    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    async def _pump_graph() -> None:
        step = 0
        try:
            async for update in compiled_graph.astream(
                initial_state,
                config=config,
                stream_mode="updates",
            ):
                step += 1
                await queue.put(("graph", (step, update)))
        except Exception as exc:
            await queue.put(("graph_error", exc))
        finally:
            await queue.put(("graph_done", None))

    async def _pump_emitter() -> None:
        try:
            async for event in emitter.events():
                await queue.put(("emitter", event))
        finally:
            await queue.put(("emitter_done", None))

    graph_task = asyncio.create_task(_pump_graph())
    emitter_task = asyncio.create_task(_pump_emitter())
    graph_done = False
    emitter_done = False

    try:
        while not (graph_done and emitter_done):
            source, payload = await queue.get()
            if source == "emitter":
                yield _event_to_dict(payload)
                continue
            if source == "graph":
                step, update = payload
                for item in _graph_update_events(
                    update,
                    step,
                    include_assistant_message_events=False,
                ):
                    yield item
                continue
            if source == "graph_error":
                raise payload
            if source == "graph_done":
                graph_done = True
                emitter.close()
                continue
            if source == "emitter_done":
                emitter_done = True
    finally:
        emitter.close()
        for task in (graph_task, emitter_task):
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
