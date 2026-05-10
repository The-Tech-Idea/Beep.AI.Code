"""Tests for the graph streaming module."""

from __future__ import annotations

from beep.agent.streaming import StreamEmitter
import pytest

from beep.agent.graph_streaming import stream_graph_events


class _FakeCompiledGraph:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    async def astream(self, initial_state, *, config, stream_mode):
        for event in self._events:
            yield event


@pytest.mark.asyncio
async def test_stream_graph_events_yields_complete_event() -> None:
    fake_graph = _FakeCompiledGraph(
        [
            {"agent": {"run_reason": "completed", "messages": []}},
        ]
    )
    events = []
    async for event in stream_graph_events(
        fake_graph,
        initial_state={"messages": []},
        config={"configurable": {"thread_id": "test"}},
    ):
        events.append(event)

    assert len(events) >= 1
    assert events[0]["type"] == "complete"
    assert events[0]["reason"] == "completed"


@pytest.mark.asyncio
async def test_stream_graph_events_yields_response_chunk() -> None:
    fake_graph = _FakeCompiledGraph(
        [
            {
                "agent": {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": "Let me help with that.",
                            "tool_calls": [],
                        }
                    ]
                }
            },
        ]
    )
    events = []
    async for event in stream_graph_events(
        fake_graph,
        initial_state={"messages": []},
        config={"configurable": {"thread_id": "test"}},
    ):
        events.append(event)

    chunk_events = [e for e in events if e["type"] == "response_chunk"]
    assert len(chunk_events) >= 1
    assert chunk_events[0]["content"] == "Let me help with that."


@pytest.mark.asyncio
async def test_stream_graph_events_yields_tool_start() -> None:
    fake_graph = _FakeCompiledGraph(
        [
            {
                "agent": {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "file_read",
                                        "arguments": '{"file_path": "test.py"}',
                                    }
                                }
                            ],
                        }
                    ]
                }
            },
        ]
    )
    events = []
    async for event in stream_graph_events(
        fake_graph,
        initial_state={"messages": []},
        config={"configurable": {"thread_id": "test"}},
    ):
        events.append(event)

    tool_events = [e for e in events if e["type"] == "tool_start"]
    assert len(tool_events) >= 1
    assert tool_events[0]["tool"] == "file_read"


@pytest.mark.asyncio
async def test_stream_graph_events_yields_policy_denied() -> None:
    fake_graph = _FakeCompiledGraph(
        [
            {
                "agent": {
                    "messages": [],
                    "pending_tool_messages": [
                        {"content": "Blocked by sandbox: cannot write outside workspace"}
                    ],
                }
            },
        ]
    )
    events = []
    async for event in stream_graph_events(
        fake_graph,
        initial_state={"messages": []},
        config={"configurable": {"thread_id": "test"}},
    ):
        events.append(event)

    denied_events = [e for e in events if e["type"] == "policy_denied"]
    assert len(denied_events) >= 1
    assert "Blocked by sandbox" in denied_events[0]["message"]


@pytest.mark.asyncio
async def test_stream_graph_events_merges_emitter_events_without_duplicate_assistant_chunks() -> None:
    fake_graph = _FakeCompiledGraph(
        [
            {
                "agent": {
                    "messages": [{"role": "assistant", "content": "post-hoc"}],
                    "run_reason": "completed",
                }
            },
        ]
    )
    emitter = StreamEmitter()
    emitter.response_chunk("live chunk", step=1)

    events = []
    async for event in stream_graph_events(
        fake_graph,
        initial_state={"messages": []},
        config={"configurable": {"thread_id": "test"}},
        emitter=emitter,
    ):
        events.append(event)

    assert any(event["type"] == "response_chunk" and event["content"] == "live chunk" for event in events)
    assert not any(event["type"] == "response_chunk" and event["content"] == "post-hoc" for event in events)
    assert any(event["type"] == "complete" and event["reason"] == "completed" for event in events)
