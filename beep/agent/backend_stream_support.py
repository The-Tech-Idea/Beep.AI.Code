"""Streaming and provider-shaping helpers for autonomous-agent backends."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from beep.agent.message_adapter import AgentCompletion
from beep.api.streaming import CompletionStreamDelta, ToolCallDelta


class CompletionStreamAccumulator:
    """Accumulate streamed deltas into a final AgentCompletion payload."""

    def __init__(self) -> None:
        self._content_parts: list[str] = []
        self._tool_calls: dict[int, dict[str, Any]] = {}
        self._usage: dict[str, int] | None = None

    def append(self, delta: CompletionStreamDelta) -> None:
        if delta.content:
            self._content_parts.append(delta.content)
        if delta.usage:
            self._usage = delta.usage
        for tool_delta in delta.tool_calls:
            entry = self._tool_calls.setdefault(
                tool_delta.index,
                {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                },
            )
            if tool_delta.id:
                entry["id"] = tool_delta.id
            if tool_delta.name:
                entry["function"]["name"] += tool_delta.name
            if tool_delta.arguments:
                entry["function"]["arguments"] += tool_delta.arguments

    def build_completion(self) -> AgentCompletion:
        content = "".join(self._content_parts).strip() or None
        tool_calls = [self._tool_calls[index] for index in sorted(self._tool_calls)]
        return AgentCompletion(
            content=content,
            tool_calls=tool_calls,
            usage=self._usage,
            raw_response={"streamed": True},
        )


async def collect_completion_stream(
    stream: AsyncIterator[CompletionStreamDelta],
) -> AgentCompletion:
    """Consume a streamed backend response into a final AgentCompletion."""
    accumulator = CompletionStreamAccumulator()
    async for delta in stream:
        accumulator.append(delta)
    return accumulator.build_completion()


async def iter_completion_as_stream(
    completion: AgentCompletion,
) -> AsyncIterator[CompletionStreamDelta]:
    """Synthesize a streamed view of a one-shot completion."""
    if completion.content:
        yield CompletionStreamDelta(content=completion.content)
    for index, tool_call in enumerate(completion.tool_calls):
        function = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
        yield CompletionStreamDelta(
            tool_calls=(
                ToolCallDelta(
                    index=index,
                    id=str(tool_call.get("id", "")) if isinstance(tool_call, dict) else None,
                    name=str(function.get("name", "")) if isinstance(function, dict) else None,
                    arguments=str(function.get("arguments", ""))
                    if isinstance(function, dict)
                    else None,
                ),
            )
        )
    if completion.usage:
        yield CompletionStreamDelta(usage=completion.usage)


def coerce_anthropic_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _parse_base64_data_image_url(url: str) -> dict[str, str] | None:
    if not isinstance(url, str) or not url.startswith("data:"):
        return None
    metadata, separator, data = url[5:].partition(",")
    if not separator or not data:
        return None
    media_type, _, encoding = metadata.partition(";")
    if encoding != "base64":
        return None
    return {
        "type": "base64",
        "media_type": media_type or "application/octet-stream",
        "data": data,
    }


def _normalize_anthropic_user_content_block(block: Any) -> dict[str, Any] | None:
    if isinstance(block, str):
        text = block.strip()
        if not text:
            return None
        return {"type": "text", "text": text}
    if not isinstance(block, dict):
        text = coerce_anthropic_text(block).strip()
        if not text:
            return None
        return {"type": "text", "text": text}

    block_type = str(block.get("type", "")).strip().lower()
    if block_type == "text":
        text = coerce_anthropic_text(block.get("text")).strip()
        if not text:
            return None
        return {"type": "text", "text": text}

    if block_type == "image":
        source = block.get("source")
        if isinstance(source, dict) and source.get("type") == "base64":
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": str(source.get("media_type", "application/octet-stream")),
                    "data": str(source.get("data", "")),
                },
            }
        raise ValueError("Anthropic vision blocks must use base64 image sources.")

    if block_type == "image_url":
        image_url = block.get("image_url")
        url = None
        if isinstance(image_url, dict):
            url = image_url.get("url")
        elif isinstance(image_url, str):
            url = image_url
        source = _parse_base64_data_image_url(str(url or ""))
        if source is None:
            raise ValueError(
                "Anthropic vision currently requires data:image/...;base64 URLs when using OpenAI-style image_url blocks."
            )
        return {"type": "image", "source": source}

    text = coerce_anthropic_text(block).strip()
    if not text:
        return None
    return {"type": "text", "text": text}


def convert_tools_to_anthropic(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    if not tools:
        return None

    anthropic_tools: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue

        function_payload = tool.get("function") if tool.get("type") == "function" else None
        if isinstance(function_payload, dict):
            anthropic_tools.append(
                {
                    "name": str(function_payload.get("name", "")),
                    "description": str(function_payload.get("description", "") or ""),
                    "input_schema": function_payload.get("parameters")
                    if isinstance(function_payload.get("parameters"), dict)
                    else {"type": "object", "properties": {}},
                }
            )
            continue

        if all(key in tool for key in ("name", "input_schema")):
            anthropic_tools.append(
                {
                    "name": str(tool.get("name", "")),
                    "description": str(tool.get("description", "") or ""),
                    "input_schema": tool.get("input_schema")
                    if isinstance(tool.get("input_schema"), dict)
                    else {"type": "object", "properties": {}},
                }
            )

    return anthropic_tools or None


def normalize_messages_for_anthropic(
    messages: list[dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    system_parts: list[str] = []
    anthropic_messages: list[dict[str, Any]] = []

    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip().lower()

        if role == "system":
            text = coerce_anthropic_text(message.get("content")).strip()
            if text:
                system_parts.append(text)
            continue

        if role == "tool":
            tool_call_id = str(message.get("tool_call_id", "")).strip()
            content = coerce_anthropic_text(message.get("content"))
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call_id,
                            "content": content,
                        }
                    ],
                }
            )
            continue

        if role == "assistant":
            content_blocks: list[dict[str, Any]] = []
            text = coerce_anthropic_text(message.get("content"))
            if text:
                content_blocks.append({"type": "text", "text": text})

            raw_tool_calls = message.get("tool_calls")
            if isinstance(raw_tool_calls, list):
                for tool_call in raw_tool_calls:
                    if not isinstance(tool_call, dict):
                        continue
                    function = tool_call.get("function", {})
                    arguments = function.get("arguments", {}) if isinstance(function, dict) else {}
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    if not isinstance(arguments, dict):
                        arguments = {}
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": str(tool_call.get("id", "")),
                            "name": str(function.get("name", "")) if isinstance(function, dict) else "",
                            "input": arguments,
                        }
                    )

            anthropic_messages.append(
                {
                    "role": "assistant",
                    "content": content_blocks or "",
                }
            )
            continue

        raw_content = message.get("content")
        if isinstance(raw_content, list):
            content_blocks = [
                block
                for block in (
                    _normalize_anthropic_user_content_block(item) for item in raw_content
                )
                if block is not None
            ]
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": content_blocks or "",
                }
            )
            continue

        anthropic_messages.append(
            {
                "role": "user",
                "content": coerce_anthropic_text(raw_content),
            }
        )

    system = "\n\n".join(part for part in system_parts if part.strip()) or None
    return system, anthropic_messages


def extract_anthropic_completion(response: dict[str, Any]) -> AgentCompletion:
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    raw_content = response.get("content", [])
    if isinstance(raw_content, list):
        for block in raw_content:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", "")).strip().lower()
            if block_type == "tool_use":
                tool_calls.append(
                    {
                        "id": str(block.get("id", "")),
                        "type": "function",
                        "function": {
                            "name": str(block.get("name", "")),
                            "arguments": json.dumps(block.get("input", {}))
                            if isinstance(block.get("input"), dict)
                            else str(block.get("input", "{}")),
                        },
                    }
                )
                continue
            text = block.get("text")
            if text is not None:
                text_parts.append(str(text))

    usage_payload = response.get("usage")
    usage: dict[str, int] | None = None
    if isinstance(usage_payload, dict):
        prompt_tokens = int(usage_payload.get("input_tokens", 0) or 0)
        completion_tokens = int(usage_payload.get("output_tokens", 0) or 0)
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens > 0:
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }

    content = "".join(text_parts).strip() or None
    return AgentCompletion(
        content=content,
        tool_calls=tool_calls,
        usage=usage,
        raw_response=response,
    )


def _build_anthropic_usage(
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, int] | None:
    total_tokens = prompt_tokens + completion_tokens
    if total_tokens <= 0:
        return None
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


async def iter_anthropic_sse_events(
    lines: AsyncIterator[str],
) -> AsyncIterator[CompletionStreamDelta]:
    """Yield normalized completion deltas from Anthropic SSE responses."""
    current_event = ""
    prompt_tokens = 0
    completion_tokens = 0

    async for line in lines:
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue

        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue

        if current_event == "message_start":
            message = payload.get("message", {}) if isinstance(payload, dict) else {}
            usage_payload = message.get("usage") if isinstance(message, dict) else None
            if isinstance(usage_payload, dict):
                prompt_tokens = int(usage_payload.get("input_tokens", 0) or 0)
                completion_tokens = int(usage_payload.get("output_tokens", 0) or 0)
                usage = _build_anthropic_usage(prompt_tokens, completion_tokens)
                if usage:
                    yield CompletionStreamDelta(usage=usage, raw_chunk=payload)
            continue

        if current_event == "message_delta":
            usage_payload = payload.get("usage") if isinstance(payload, dict) else None
            if isinstance(usage_payload, dict):
                prompt_tokens = int(usage_payload.get("input_tokens", prompt_tokens) or prompt_tokens)
                completion_tokens = int(
                    usage_payload.get("output_tokens", completion_tokens) or completion_tokens
                )
                usage = _build_anthropic_usage(prompt_tokens, completion_tokens)
                if usage:
                    yield CompletionStreamDelta(usage=usage, raw_chunk=payload)
            continue

        if current_event == "content_block_start":
            block = payload.get("content_block", {}) if isinstance(payload, dict) else {}
            index = int(payload.get("index", 0) or 0) if isinstance(payload, dict) else 0
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", "")).strip().lower()
            if block_type == "text":
                text = block.get("text")
                if text:
                    yield CompletionStreamDelta(content=str(text), raw_chunk=payload)
                continue
            if block_type == "tool_use":
                tool_id = block.get("id")
                tool_name = block.get("name")
                if tool_id or tool_name:
                    yield CompletionStreamDelta(
                        tool_calls=(
                            ToolCallDelta(
                                index=index,
                                id=str(tool_id) if tool_id is not None else None,
                                name=str(tool_name) if tool_name is not None else None,
                            ),
                        ),
                        raw_chunk=payload,
                    )
            continue

        if current_event == "content_block_delta":
            delta = payload.get("delta", {}) if isinstance(payload, dict) else {}
            index = int(payload.get("index", 0) or 0) if isinstance(payload, dict) else 0
            if not isinstance(delta, dict):
                continue
            delta_type = str(delta.get("type", "")).strip().lower()
            if delta_type == "text_delta":
                text = delta.get("text")
                if text:
                    yield CompletionStreamDelta(content=str(text), raw_chunk=payload)
                continue
            if delta_type == "input_json_delta":
                partial_json = delta.get("partial_json")
                if partial_json:
                    yield CompletionStreamDelta(
                        tool_calls=(ToolCallDelta(index=index, arguments=str(partial_json)),),
                        raw_chunk=payload,
                    )