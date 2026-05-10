"""Typed request helpers for autonomous-agent model backends."""

from __future__ import annotations

from collections.abc import AsyncIterator
import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from beep.agent.backend_stream_support import iter_completion_as_stream
from beep.api.streaming import CompletionStreamDelta

if TYPE_CHECKING:
    from beep.agent.backends import AgentCompletion, AgentModelBackend


@dataclass(frozen=True)
class AgentCompletionRequest:
    """Request envelope for one backend completion call."""

    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    stream: bool = False
    response_format: dict[str, Any] | None = None
    provider_options: dict[str, Any] | None = None


def _supports_parameter(signature: inspect.Signature, name: str) -> bool:
    if name in signature.parameters:
        return True
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _build_completion_kwargs(
    signature: inspect.Signature | None,
    request: AgentCompletionRequest,
    *,
    include_stream: bool,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "messages": request.messages,
        "tools": request.tools,
    }
    if include_stream and request.stream and (
        signature is None or _supports_parameter(signature, "stream")
    ):
        kwargs["stream"] = True
    if request.response_format is not None and (
        signature is None or _supports_parameter(signature, "response_format")
    ):
        kwargs["response_format"] = request.response_format
    if request.provider_options and (
        signature is None or _supports_parameter(signature, "provider_options")
    ):
        kwargs["provider_options"] = request.provider_options
    return kwargs


async def complete_agent_completion_request(
    backend: AgentModelBackend,
    request: AgentCompletionRequest,
) -> AgentCompletion:
    """Invoke a backend completion while preserving compatibility with older plugins."""

    complete = getattr(backend, "complete")
    try:
        signature = inspect.signature(complete)
    except (TypeError, ValueError):
        signature = None

    kwargs = _build_completion_kwargs(signature, request, include_stream=True)
    return await complete(**kwargs)


async def stream_agent_completion_request(
    backend: AgentModelBackend,
    request: AgentCompletionRequest,
) -> AsyncIterator[CompletionStreamDelta]:
    """Invoke a streaming backend completion with legacy-backend fallback."""

    stream_complete = getattr(backend, "stream_complete", None)
    if callable(stream_complete):
        try:
            signature = inspect.signature(stream_complete)
        except (TypeError, ValueError):
            signature = None
        kwargs = _build_completion_kwargs(signature, request, include_stream=False)
        async for delta in stream_complete(**kwargs):
            yield delta
        return

    completion = await complete_agent_completion_request(backend, request)
    async for delta in iter_completion_as_stream(completion):
        yield delta