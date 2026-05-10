"""Provider-neutral model backends for the autonomous agent."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

import httpx

from beep.agent.backend_stream_support import (
    collect_completion_stream,
    convert_tools_to_anthropic,
    extract_anthropic_completion,
    iter_anthropic_sse_events,
    normalize_messages_for_anthropic,
)
from beep.agent.message_adapter import AgentCompletion, extract_agent_completion
from beep.api.client import BeepAPIClient
from beep.api.errors import BeepAPIError
from beep.api.streaming import CompletionStreamDelta, iter_chat_sse_events
from beep.config import BeepConfig


ANTHROPIC_API_VERSION = "2023-06-01"
_OPENAI_RESERVED_COMPLETION_FIELDS = frozenset(
    {"messages", "tools", "model", "response_format", "stream"}
)
_ANTHROPIC_RESERVED_COMPLETION_FIELDS = frozenset(
    {"messages", "tools", "model", "max_tokens", "system", "stream"}
)


@runtime_checkable
class AgentModelBackend(Protocol):
    """Protocol implemented by model backends used by the autonomous agent."""

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> AgentCompletion:
        """Run one model completion."""

    async def close(self) -> None:
        """Release any transport resources owned by the backend."""


class BeepAgentBackend:
    """Backend that calls the Beep.AI.Server OpenAI-compatible chat surface."""

    def __init__(
        self,
        client: Any,
        *,
        model: str | None = None,
        coding_assistant: dict[str, Any] | None = None,
        owns_client: bool = False,
    ) -> None:
        self._client = client
        self._model = model
        self._coding_assistant = coding_assistant
        self._owns_client = owns_client

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> AgentCompletion:
        if stream:
            return await collect_completion_stream(
                self.stream_complete(
                    messages=messages,
                    tools=tools,
                    response_format=response_format,
                    provider_options=provider_options,
                )
            )
        if provider_options:
            raise ValueError(
                "Provider-specific Beep completion options are not yet exposed by the autonomous-agent backend."
            )
        response = await self._client.chat_completion(
            messages=messages,
            model=self._model,
            tools=tools,
            coding_assistant=self._coding_assistant,
            response_format=response_format,
        )
        return extract_agent_completion(response)

    async def stream_complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> AsyncIterator[CompletionStreamDelta]:
        if provider_options:
            raise ValueError(
                "Provider-specific Beep completion options are not yet exposed by the autonomous-agent backend."
            )
        async for event in self._client.chat_completion_event_stream(
            messages=messages,
            model=self._model,
            tools=tools,
            coding_assistant=self._coding_assistant,
            response_format=response_format,
        ):
            yield event

    async def close(self) -> None:
        if not self._owns_client:
            return None
        close = getattr(self._client, "close", None)
        if close is None or not callable(close):
            return None
        result = close()
        if inspect.isawaitable(result):
            await result
        return None


class OpenAICompatibleAgentBackend:
    """Backend that calls a generic OpenAI-compatible chat completion endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model: str | None,
        request_timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None

    def _normalized_base_url(self) -> str:
        return self._base_url.rstrip("/") + "/"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(
                base_url=self._normalized_base_url(),
                headers=headers,
                timeout=httpx.Timeout(self._request_timeout, connect=10.0),
            )
        return self._client

    def _build_payload(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        response_format: dict[str, Any] | None,
        provider_options: dict[str, Any] | None,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"messages": messages}
        if self._model:
            payload["model"] = self._model
        if tools:
            payload["tools"] = tools
        if response_format is not None:
            payload["response_format"] = response_format
        if stream:
            payload["stream"] = True
        if provider_options:
            for key, value in provider_options.items():
                if key in _OPENAI_RESERVED_COMPLETION_FIELDS:
                    continue
                payload[key] = value
        return payload

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> AgentCompletion:
        if stream:
            return await collect_completion_stream(
                self.stream_complete(
                    messages=messages,
                    tools=tools,
                    response_format=response_format,
                    provider_options=provider_options,
                )
            )
        payload = self._build_payload(
            messages=messages,
            tools=tools,
            response_format=response_format,
            provider_options=provider_options,
            stream=False,
        )
        client = await self._get_client()
        response = await client.post("v1/chat/completions", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.text
            except Exception:
                detail = str(exc)
            raise BeepAPIError(exc.response.status_code, "/v1/chat/completions", detail) from exc
        return extract_agent_completion(response.json())

    async def stream_complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> AsyncIterator[CompletionStreamDelta]:
        payload = self._build_payload(
            messages=messages,
            tools=tools,
            response_format=response_format,
            provider_options=provider_options,
            stream=True,
        )
        client = await self._get_client()
        async with client.stream("POST", "v1/chat/completions", json=payload) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    detail = exc.response.text
                except Exception:
                    detail = str(exc)
                raise BeepAPIError(exc.response.status_code, "/v1/chat/completions", detail) from exc
            async for delta in iter_chat_sse_events(response.aiter_lines()):
                yield delta

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

class AnthropicMessagesAgentBackend:
    """Backend that calls Anthropic's Messages API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int = 4096,
        request_timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                },
                timeout=httpx.Timeout(self._request_timeout, connect=10.0),
            )
        return self._client

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> AgentCompletion:
        if stream:
            return await collect_completion_stream(
                self.stream_complete(
                    messages=messages,
                    tools=tools,
                    response_format=response_format,
                    provider_options=provider_options,
                )
            )
        if response_format is not None:
            raise ValueError(
                "Structured response_format is not yet exposed by the Anthropic autonomous-agent backend."
            )
        system, anthropic_messages = normalize_messages_for_anthropic(messages)
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": self._max_tokens,
        }
        if system:
            payload["system"] = system
        anthropic_tools = convert_tools_to_anthropic(tools)
        if anthropic_tools:
            payload["tools"] = anthropic_tools
        if provider_options:
            for key, value in provider_options.items():
                if key in _ANTHROPIC_RESERVED_COMPLETION_FIELDS:
                    continue
                payload[key] = value

        client = await self._get_client()
        response = await client.post("/v1/messages", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.text
            except Exception:
                detail = str(exc)
            raise BeepAPIError(exc.response.status_code, "/v1/messages", detail) from exc
        return extract_anthropic_completion(response.json())

    async def stream_complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> AsyncIterator[CompletionStreamDelta]:
        if response_format is not None:
            raise ValueError(
                "Structured response_format is not yet exposed by the Anthropic autonomous-agent backend."
            )
        system, anthropic_messages = normalize_messages_for_anthropic(messages)
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": self._max_tokens,
            "stream": True,
        }
        if system:
            payload["system"] = system
        anthropic_tools = convert_tools_to_anthropic(tools)
        if anthropic_tools:
            payload["tools"] = anthropic_tools
        if provider_options:
            for key, value in provider_options.items():
                if key in _ANTHROPIC_RESERVED_COMPLETION_FIELDS:
                    continue
                payload[key] = value

        client = await self._get_client()
        async with client.stream("POST", "/v1/messages", json=payload) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    detail = exc.response.text
                except Exception:
                    detail = str(exc)
                raise BeepAPIError(exc.response.status_code, "/v1/messages", detail) from exc
            async for delta in iter_anthropic_sse_events(response.aiter_lines()):
                yield delta

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None


def coerce_agent_backend(
    model_client: Any,
    *,
    coding_assistant: dict[str, Any] | None = None,
    model: str | None = None,
) -> AgentModelBackend:
    """Convert a provided backend/client object into the autonomous agent backend contract."""
    if isinstance(model_client, AgentModelBackend):
        return model_client
    if hasattr(model_client, "complete") and callable(model_client.complete):
        return model_client
    if hasattr(model_client, "chat_completion") and callable(model_client.chat_completion):
        return BeepAgentBackend(
            model_client,
            model=model,
            coding_assistant=coding_assistant,
        )
    raise TypeError(
        "Unsupported agent backend object. Expected an AgentModelBackend or an object with chat_completion()."
    )


def build_agent_backend(
    config: BeepConfig,
    *,
    client: Any = None,
    coding_assistant: dict[str, Any] | None = None,
    plugin_registry: Any | None = None,
) -> AgentModelBackend:
    """Create the configured backend for the autonomous agent."""
    from beep.agent.provider_plugins import get_agent_backend_provider

    provider = get_agent_backend_provider(
        config.agent_backend,
        plugin_registry=plugin_registry,
    )
    return provider.build_backend(
        config,
        client=client,
        coding_assistant=coding_assistant,
    )