"""Focused regression tests for streamed autonomous-agent completions."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from beep.agent.backend_requests import AgentCompletionRequest, stream_agent_completion_request
from beep.agent.backends import (
    AgentCompletion,
    AnthropicMessagesAgentBackend,
    BeepAgentBackend,
)
from beep.api.streaming import CompletionStreamDelta, ToolCallDelta


@pytest.mark.asyncio
async def test_beep_backend_streaming_uses_event_stream() -> None:
    async def _events():
        yield CompletionStreamDelta(content="Hello")
        yield CompletionStreamDelta(
            tool_calls=(
                ToolCallDelta(
                    index=0,
                    id="call-1",
                    name="file_read",
                    arguments="{}",
                ),
            )
        )

    client = MagicMock()
    client.chat_completion_event_stream = MagicMock(return_value=_events())
    backend = BeepAgentBackend(
        client,
        model="model-a",
        coding_assistant={"project_id": 12},
    )

    result = await backend.complete(
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
    )

    assert result.content == "Hello"
    assert result.tool_calls[0]["function"]["name"] == "file_read"
    _, kwargs = client.chat_completion_event_stream.call_args
    assert kwargs["model"] == "model-a"
    assert kwargs["coding_assistant"] == {"project_id": 12}


@pytest.mark.asyncio
async def test_stream_agent_completion_request_falls_back_to_complete() -> None:
    class LegacyBackend:
        async def complete(
            self,
            *,
            messages: list[dict[str, object]],
            tools: list[dict[str, object]] | None = None,
        ) -> AgentCompletion:
            del messages, tools
            return AgentCompletion(
                content="legacy",
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "file_read", "arguments": "{}"},
                    }
                ],
                usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            )

    events = [
        delta
        async for delta in stream_agent_completion_request(
            LegacyBackend(),
            AgentCompletionRequest(messages=[{"role": "user", "content": "hello"}], stream=True),
        )
    ]

    assert [delta.content for delta in events if delta.content] == ["legacy"]
    assert any(delta.tool_calls and delta.tool_calls[0].name == "file_read" for delta in events)
    assert any(delta.usage == {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3} for delta in events)


@pytest.mark.asyncio
async def test_anthropic_backend_streaming_requests_assemble_completion() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        lines = [
            "event: message_start",
            f"data: {json.dumps({'message': {'usage': {'input_tokens': 2, 'output_tokens': 0}}})}",
            "event: content_block_start",
            f"data: {json.dumps({'index': 0, 'content_block': {'type': 'text', 'text': 'Hello'}})}",
            "event: content_block_delta",
            f"data: {json.dumps({'index': 0, 'delta': {'type': 'text_delta', 'text': ' there'}})}",
            "event: content_block_start",
            f"data: {json.dumps({'index': 1, 'content_block': {'type': 'tool_use', 'id': 'call-1', 'name': 'file_read'}})}",
            "event: content_block_delta",
            f"data: {json.dumps({'index': 1, 'delta': {'type': 'input_json_delta', 'partial_json': '{\"file_path\":\"x.txt\"}'}})}",
            "event: message_delta",
            f"data: {json.dumps({'usage': {'output_tokens': 4}})}",
            "data: [DONE]",
        ]
        return httpx.Response(200, text="\n".join(lines))

    backend = AnthropicMessagesAgentBackend(
        base_url="https://api.anthropic.com",
        api_key="anthropic-token",
        model="claude-sonnet-4-20250514",
        request_timeout=10.0,
    )
    backend._client = httpx.AsyncClient(
        base_url="https://api.anthropic.com",
        headers={
            "x-api-key": "anthropic-token",
            "anthropic-version": "2023-06-01",
        },
        transport=httpx.MockTransport(handler),
    )

    try:
        result = await backend.complete(
            messages=[{"role": "user", "content": "hello"}],
            stream=True,
        )
    finally:
        await backend.close()

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["stream"] is True
    assert result.content == "Hello there"
    assert result.tool_calls == [
        {
            "id": "call-1",
            "type": "function",
            "function": {"name": "file_read", "arguments": '{"file_path":"x.txt"}'},
        }
    ]
    assert result.usage == {"prompt_tokens": 2, "completion_tokens": 4, "total_tokens": 6}