"""Stream event emitter for agent execution."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from beep.agent.streaming.event_types import (
    AgentEvent,
    CompleteEvent,
    NodeEndEvent,
    NodeStartEvent,
    ResponseChunkEvent,
    ToolResultEvent,
    ToolStartEvent,
)

_SENTINEL = object()


class StreamEmitter:
    """Buffered event emitter for streaming agent execution.

    Events are emitted via an async iterator. Consumers await
    events as they are produced.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[AgentEvent | object] = asyncio.Queue()
        self._done = False
        self._history: deque[AgentEvent] = deque(maxlen=100)

    def emit(self, event: AgentEvent) -> None:
        """Add an event to the stream."""
        self._history.append(event)
        self._queue.put_nowait(event)

    def node_start(self, node: str, step: int = 0) -> None:
        self.emit(NodeStartEvent(type="node_start", step=step, node=node))

    def node_end(self, node: str, step: int = 0, output: dict[str, Any] | None = None) -> None:
        self.emit(
            NodeEndEvent(
                type="node_end",
                step=step,
                node=node,
                output=output or {},
            )
        )

    def tool_start(self, tool: str, input: dict[str, Any] | None = None, step: int = 0) -> None:
        self.emit(
            ToolStartEvent(
                type="tool_start",
                step=step,
                tool=tool,
                input=input or {},
            )
        )

    def tool_result(self, tool: str, output: str, success: bool = True, step: int = 0) -> None:
        self.emit(
            ToolResultEvent(
                type="tool_result",
                step=step,
                tool=tool,
                output=output[:500],
                success=success,
            )
        )

    def response_chunk(self, content: str, step: int = 0) -> None:
        self.emit(ResponseChunkEvent(type="response_chunk", step=step, content=content))

    def complete(self, reason: str = "", final_message: str = "", step: int = 0) -> None:
        if self._done:
            return
        self._done = True
        self.emit(
            CompleteEvent(
                type="complete",
                step=step,
                reason=reason,
                final_message=final_message,
            )
        )
        self._queue.put_nowait(_SENTINEL)

    def close(self) -> None:
        """Stop the event stream without emitting a completion event."""
        if self._done:
            return
        self._done = True
        self._queue.put_nowait(_SENTINEL)

    async def events(self) -> AgentEvent:
        """Async iterator over emitted events."""
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item  # type: ignore[arg-type]

    @property
    def history(self) -> list[AgentEvent]:
        return list(self._history)
