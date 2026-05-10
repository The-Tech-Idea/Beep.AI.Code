"""Streaming response parsing for Beep.AI.Server APIs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

# Sentinel prefix used to signal a tool-call event through the text stream.
# Format: \x00TC:<tool_name>\x00
TOOL_CALL_PREFIX = "\x00TC:"
TOOL_CALL_SUFFIX = "\x00"


@dataclass(frozen=True)
class ToolCallDelta:
    """Incremental tool-call data from a streaming completion."""

    index: int = 0
    id: str | None = None
    name: str | None = None
    arguments: str | None = None


@dataclass(frozen=True)
class CompletionStreamDelta:
    """One normalized streaming completion delta."""

    content: str = ""
    tool_calls: tuple[ToolCallDelta, ...] = field(default_factory=tuple)
    usage: dict[str, int] | None = None
    raw_chunk: dict[str, Any] | None = None


def _normalize_usage(usage: Any) -> dict[str, int] | None:
    if not isinstance(usage, dict):
        return None
    total_tokens = int(usage.get("total_tokens", 0) or 0)
    if total_tokens <= 0:
        return None
    return {
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": total_tokens,
    }


def _stringify_delta_field(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


async def iter_chat_sse_events(
    lines: AsyncIterable[str],
) -> AsyncIterator[CompletionStreamDelta]:
    """Yield normalized deltas from OpenAI-style chat completion SSE lines."""
    async for line in lines:
        if not line or not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue

        normalized_usage = _normalize_usage(chunk.get("usage"))
        choices = chunk.get("choices", [])
        if not choices:
            if normalized_usage:
                yield CompletionStreamDelta(usage=normalized_usage, raw_chunk=chunk)
            continue

        choice = choices[0] if isinstance(choices[0], dict) else {}
        delta = choice.get("delta", {}) if isinstance(choice, dict) else {}
        content = str(delta.get("content", "") or "") if isinstance(delta, dict) else ""
        tool_call_deltas: list[ToolCallDelta] = []
        raw_tool_calls = delta.get("tool_calls", []) if isinstance(delta, dict) else []
        if isinstance(raw_tool_calls, list):
            for raw_tool_call in raw_tool_calls:
                if not isinstance(raw_tool_call, dict):
                    continue
                function = raw_tool_call.get("function", {})
                tool_call_deltas.append(
                    ToolCallDelta(
                        index=int(raw_tool_call.get("index", 0) or 0),
                        id=_stringify_delta_field(raw_tool_call.get("id")),
                        name=_stringify_delta_field(
                            function.get("name") if isinstance(function, dict) else None
                        ),
                        arguments=_stringify_delta_field(
                            function.get("arguments") if isinstance(function, dict) else None
                        ),
                    )
                )

        if content or tool_call_deltas or normalized_usage:
            yield CompletionStreamDelta(
                content=content,
                tool_calls=tuple(tool_call_deltas),
                usage=normalized_usage,
                raw_chunk=chunk,
            )


async def iter_chat_sse_content(
    lines: AsyncIterable[str],
) -> AsyncIterator[tuple[str, dict[str, int] | None]]:
    """Yield content chunks and optional usage from OpenAI-style SSE lines.

    When a streaming delta contains ``tool_calls``, a sentinel marker of the
    form ``\x00TC:<name>\x00`` is emitted so renderers can display tool-call
    activity without receiving real text content.
    """
    async for delta in iter_chat_sse_events(lines):
        for tool_call in delta.tool_calls:
            if tool_call.name:
                yield f"{TOOL_CALL_PREFIX}{tool_call.name}{TOOL_CALL_SUFFIX}", None
        if delta.content or delta.usage:
            yield delta.content, delta.usage
