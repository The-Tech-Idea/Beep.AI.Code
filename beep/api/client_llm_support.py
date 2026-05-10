"""LLM-facing endpoint helpers for the API client."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from beep.api.payloads import build_chat_completion_payload
from beep.api.streaming import (
    CompletionStreamDelta,
    TOOL_CALL_PREFIX,
    TOOL_CALL_SUFFIX,
    iter_chat_sse_events,
)

if TYPE_CHECKING:
    from beep.api.client import BeepAPIClient


class BeepAPIClientLLMMixin:
    async def health_check(self) -> dict[str, Any]:
        return await health_check(self)

    async def v1_health(self) -> dict[str, Any]:
        return await v1_health(self)

    async def list_models(self) -> list[dict[str, Any]]:
        return await list_models(self)

    async def get_model(self, model_id: str) -> dict[str, Any]:
        return await get_model(self, model_id)

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        coding_assistant: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del stream
        return await chat_completion(
            self,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            coding_assistant=coding_assistant,
            response_format=response_format,
        )

    async def chat_completion_stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        coding_assistant: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in chat_completion_stream(
            self,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            coding_assistant=coding_assistant,
            response_format=response_format,
        ):
            yield chunk

    async def chat_completion_event_stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        coding_assistant: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> AsyncGenerator[CompletionStreamDelta, None]:
        async for event in chat_completion_event_stream(
            self,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            coding_assistant=coding_assistant,
            response_format=response_format,
        ):
            yield event

    def get_last_stream_usage(self) -> dict[str, int] | None:
        return get_last_stream_usage(self)

    async def anthropic_messages(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 4096,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        thinking: dict[str, Any] | None = None,
        beta_features: list[str] | None = None,
    ) -> dict[str, Any]:
        return await anthropic_messages(
            self,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            thinking=thinking,
            beta_features=beta_features,
        )

    async def responses_completion(
        self,
        input_text: str,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return await responses_completion(
            self,
            input_text=input_text,
            model=model,
            tools=tools,
        )

    async def openai_responses(
        self,
        input: str | list[dict[str, Any]],
        model: str | None = None,
        previous_response_id: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        reasoning: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await openai_responses(
            self,
            input=input,
            model=model,
            previous_response_id=previous_response_id,
            tools=tools,
            reasoning=reasoning,
        )

    async def create_embeddings(
        self,
        input_texts: list[str],
        model: str | None = None,
    ) -> dict[str, Any]:
        return await create_embeddings(self, input_texts=input_texts, model=model)


async def health_check(client: BeepAPIClient) -> dict[str, Any]:
    return await client._request("GET", "/api/health")


async def v1_health(client: BeepAPIClient) -> dict[str, Any]:
    return await client._request("GET", "/v1/health")


async def list_models(client: BeepAPIClient) -> list[dict[str, Any]]:
    data = await client._request("GET", "/v1/models")
    return data.get("data", [])


async def get_model(client: BeepAPIClient, model_id: str) -> dict[str, Any]:
    return await client._request("GET", f"/v1/models/{model_id}")


async def chat_completion(
    client: BeepAPIClient,
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    tools: list[dict[str, Any]] | None = None,
    coding_assistant: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_chat_completion_payload(
        client._config,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        tools=tools,
        coding_assistant=coding_assistant,
        response_format=response_format,
    )
    return await client._request("POST", "/v1/chat/completions", json=payload)


async def chat_completion_stream(
    client: BeepAPIClient,
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    tools: list[dict[str, Any]] | None = None,
    coding_assistant: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> AsyncGenerator[str, None]:
    async for event in chat_completion_event_stream(
        client,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        tools=tools,
        coding_assistant=coding_assistant,
        response_format=response_format,
    ):
        for tool_call in event.tool_calls:
            if tool_call.name:
                yield f"{TOOL_CALL_PREFIX}{tool_call.name}{TOOL_CALL_SUFFIX}"
        if event.content:
            yield event.content


async def chat_completion_event_stream(
    client: BeepAPIClient,
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    tools: list[dict[str, Any]] | None = None,
    coding_assistant: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> AsyncGenerator[CompletionStreamDelta, None]:
    http_client = await client._get_client()
    client._last_stream_usage = None
    payload = build_chat_completion_payload(
        client._config,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        tools=tools,
        coding_assistant=coding_assistant,
        response_format=response_format,
    )

    async with http_client.stream("POST", "/v1/chat/completions", json=payload) as response:
        response.raise_for_status()
        async for event in iter_chat_sse_events(response.aiter_lines()):
            if event.usage:
                client._last_stream_usage = event.usage
            yield event


def get_last_stream_usage(client: BeepAPIClient) -> dict[str, int] | None:
    return client._last_stream_usage


async def anthropic_messages(
    client: BeepAPIClient,
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int = 4096,
    system: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    thinking: dict[str, Any] | None = None,
    beta_features: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if model or client._config.default_model:
        payload["model"] = model or client._config.default_model
    if system:
        payload["system"] = system
    if tools:
        payload["tools"] = tools
    if thinking:
        payload["thinking"] = thinking

    extra_headers: dict[str, str] | None = None
    if beta_features:
        extra_headers = {"anthropic-beta": ",".join(beta_features)}

    return await client._request(
        "POST",
        "/v1/messages",
        json=payload,
        extra_headers=extra_headers,
    )


async def responses_completion(
    client: BeepAPIClient,
    *,
    input_text: str,
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return await openai_responses(client, input=input_text, model=model, tools=tools)


async def openai_responses(
    client: BeepAPIClient,
    *,
    input: str | list[dict[str, Any]],
    model: str | None = None,
    previous_response_id: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    reasoning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"input": input}
    if model or client._config.default_model:
        payload["model"] = model or client._config.default_model
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id
    if tools:
        payload["tools"] = tools
    if reasoning:
        payload["reasoning"] = reasoning
    return await client._request("POST", "/v1/responses", json=payload)


async def create_embeddings(
    client: BeepAPIClient,
    *,
    input_texts: list[str],
    model: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"input": input_texts}
    if model:
        payload["model"] = model
    return await client._request("POST", "/v1/embeddings", json=payload)