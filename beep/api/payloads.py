"""Request payload builders for Beep.AI.Server API calls."""

from __future__ import annotations

from typing import Any

from beep.config import BeepConfig


def build_chat_completion_payload(
    config: BeepConfig,
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    stream: bool = False,
    tools: list[dict[str, Any]] | None = None,
    coding_assistant: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical OpenAI-compatible chat payload."""
    payload: dict[str, Any] = {"messages": messages}
    if stream:
        payload["stream"] = True
    if model or config.default_model:
        payload["model"] = model or config.default_model
    if max_tokens:
        payload["max_tokens"] = max_tokens
    elif config.max_tokens:
        payload["max_tokens"] = config.max_tokens
    payload["temperature"] = temperature if temperature is not None else config.temperature
    if tools:
        payload["tools"] = tools
    if coding_assistant:
        payload["coding_assistant"] = coding_assistant
    if response_format is not None:
        payload["response_format"] = response_format
    return payload


def build_anthropic_messages_payload(
    config: BeepConfig,
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int = 4096,
    system: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    thinking: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an Anthropic Messages API payload.

    Caller is responsible for injecting the ``anthropic-beta`` header when
    ``beta_features`` are needed — this builder only constructs the body.
    """
    payload: dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if model or config.default_model:
        payload["model"] = model or config.default_model
    if system:
        payload["system"] = system
    if tools:
        payload["tools"] = tools
    if thinking:
        payload["thinking"] = thinking
    return payload


def build_openai_responses_payload(
    config: BeepConfig,
    *,
    input: str | list[dict[str, Any]],
    model: str | None = None,
    previous_response_id: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    reasoning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an OpenAI Responses API payload."""
    payload: dict[str, Any] = {"input": input}
    if model or config.default_model:
        payload["model"] = model or config.default_model
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id
    if tools:
        payload["tools"] = tools
    if reasoning:
        payload["reasoning"] = reasoning
    return payload
