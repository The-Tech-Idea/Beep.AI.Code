"""Tests for the streaming event module."""

from __future__ import annotations

import asyncio
import pytest

from beep.agent.streaming import StreamEmitter
from beep.agent.streaming.event_types import (
    CompleteEvent,
    NodeEndEvent,
    NodeStartEvent,
    ToolResultEvent,
    ToolStartEvent,
)


class TestEventTypes:
    def test_node_start_event(self) -> None:
        event = NodeStartEvent(type="node_start", step=1, node="agent")
        assert event.type == "node_start"
        assert event.step == 1
        assert event.node == "agent"

    def test_tool_start_event(self) -> None:
        event = ToolStartEvent(
            type="tool_start",
            step=2,
            tool="file_read",
            input={"file_path": "test.py"},
        )
        assert event.tool == "file_read"
        assert event.input["file_path"] == "test.py"

    def test_complete_event(self) -> None:
        event = CompleteEvent(
            type="complete",
            step=5,
            reason="completed",
            final_message="Done",
        )
        assert event.reason == "completed"
        assert event.final_message == "Done"


class TestStreamEmitter:
    def test_emit_adds_to_history(self) -> None:
        emitter = StreamEmitter()
        emitter.node_start("agent", step=1)
        assert len(emitter.history) == 1
        assert isinstance(emitter.history[0], NodeStartEvent)

    def test_convenience_methods(self) -> None:
        emitter = StreamEmitter()
        emitter.node_start("agent")
        emitter.tool_start("file_read", {"file": "x.py"})
        emitter.tool_result("file_read", "content")
        emitter.node_end("agent")
        emitter.complete("completed", "done")

        assert len(emitter.history) == 5
        assert isinstance(emitter.history[0], NodeStartEvent)
        assert isinstance(emitter.history[1], ToolStartEvent)
        assert isinstance(emitter.history[2], ToolResultEvent)
        assert isinstance(emitter.history[3], NodeEndEvent)
        assert isinstance(emitter.history[4], CompleteEvent)

    @pytest.mark.asyncio
    async def test_async_iterator(self) -> None:
        emitter = StreamEmitter()
        emitter.node_start("agent")
        emitter.complete("done")

        events = []
        async for event in emitter.events():
            events.append(event)

        assert len(events) == 2
        assert isinstance(events[0], NodeStartEvent)
        assert isinstance(events[1], CompleteEvent)

    def test_history_respects_maxlen(self) -> None:
        emitter = StreamEmitter()
        for i in range(150):
            emitter.node_start(f"node-{i}", step=i)
        assert len(emitter.history) == 100
