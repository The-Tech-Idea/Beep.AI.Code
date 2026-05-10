"""Tests for provider-neutral autonomous-agent backends."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from beep.agent.backend_requests import AgentCompletionRequest, complete_agent_completion_request
from beep.agent.backends import (
    AgentCompletion,
    AnthropicMessagesAgentBackend,
    BeepAgentBackend,
    OpenAICompatibleAgentBackend,
    build_agent_backend,
    extract_agent_completion,
)
from beep.agent.provider_plugins import (
    ProviderProbeResult,
    get_agent_backend_provider,
    list_agent_backend_providers,
    probe_agent_backend_configuration,
)
from beep.config import BeepConfig


def test_extract_agent_completion_normalizes_tool_calls() -> None:
    completion = extract_agent_completion(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "file_read",
                                    "arguments": {"file_path": "x.txt"},
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        }
    )
    assert completion.tool_calls[0]["function"]["name"] == "file_read"
    assert completion.tool_calls[0]["function"]["arguments"] == json.dumps({"file_path": "x.txt"})
    assert completion.usage == {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}


@pytest.mark.asyncio
async def test_beep_backend_attaches_coding_metadata() -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "done", "tool_calls": []}}],
            "usage": {"total_tokens": 5},
        }
    )
    backend = BeepAgentBackend(
        client,
        model="model-a",
        coding_assistant={"project_id": 12},
    )

    result = await backend.complete(
        messages=[{"role": "user", "content": "hello"}],
        tools=[{"type": "function", "function": {"name": "file_read", "parameters": {}}}],
    )

    assert isinstance(result, AgentCompletion)
    _, kwargs = client.chat_completion.await_args
    assert kwargs["model"] == "model-a"
    assert kwargs["coding_assistant"] == {"project_id": 12}


@pytest.mark.asyncio
async def test_beep_backend_forwards_response_format() -> None:
    client = MagicMock()
    client.chat_completion = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "done", "tool_calls": []}}],
            "usage": {"total_tokens": 5},
        }
    )
    backend = BeepAgentBackend(client, model="model-a")

    result = await backend.complete(
        messages=[{"role": "user", "content": "hello"}],
        response_format={"type": "json_object"},
    )

    assert result.content == "done"
    _, kwargs = client.chat_completion.await_args
    assert kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_complete_agent_completion_request_keeps_legacy_backends_working() -> None:
    captured: dict[str, object] = {}

    class LegacyBackend:
        async def complete(
            self,
            *,
            messages: list[dict[str, object]],
            tools: list[dict[str, object]] | None = None,
        ) -> AgentCompletion:
            captured["messages"] = messages
            captured["tools"] = tools
            return AgentCompletion(content="legacy", tool_calls=[])

        async def close(self) -> None:
            return None

    result = await complete_agent_completion_request(
        LegacyBackend(),
        AgentCompletionRequest(
            messages=[{"role": "user", "content": "hello"}],
            tools=[{"type": "function", "function": {"name": "file_read", "parameters": {}}}],
            stream=True,
            response_format={"type": "json_object"},
            provider_options={"parallel_tool_calls": False},
        ),
    )

    assert result.content == "legacy"
    assert captured["messages"] == [{"role": "user", "content": "hello"}]
    assert captured["tools"] == [
        {"type": "function", "function": {"name": "file_read", "parameters": {}}}
    ]


@pytest.mark.asyncio
async def test_beep_backend_closes_owned_client() -> None:
    client = MagicMock()
    client.close = AsyncMock()
    backend = BeepAgentBackend(client, owns_client=True)

    await backend.close()

    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_openai_compatible_backend_posts_standard_chat_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "done", "tool_calls": []}}],
                "usage": {"total_tokens": 9},
            },
        )

    backend = OpenAICompatibleAgentBackend(
        base_url="http://provider.test",
        api_key="provider-token",
        model="gpt-test",
        request_timeout=10.0,
    )
    backend._client = httpx.AsyncClient(
        base_url="http://provider.test",
        headers={"Authorization": "Bearer provider-token"},
        transport=httpx.MockTransport(handler),
    )

    try:
        result = await backend.complete(
            messages=[{"role": "user", "content": "hello"}],
            tools=[{"type": "function", "function": {"name": "file_read", "parameters": {}}}],
        )
    finally:
        await backend.close()

    assert result.content == "done"
    assert captured["path"] == "/v1/chat/completions"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers.get("authorization") == "Bearer provider-token"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-test"
    assert "coding_assistant" not in payload
    assert payload["messages"][0]["content"] == "hello"


@pytest.mark.asyncio
async def test_openai_compatible_backend_forwards_response_format_and_provider_options() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "done", "tool_calls": []}}],
                "usage": {"total_tokens": 4},
            },
        )

    backend = OpenAICompatibleAgentBackend(
        base_url="http://provider.test",
        api_key="provider-token",
        model="gpt-test",
        request_timeout=10.0,
    )
    backend._client = httpx.AsyncClient(
        base_url="http://provider.test",
        headers={"Authorization": "Bearer provider-token"},
        transport=httpx.MockTransport(handler),
    )

    try:
        result = await backend.complete(
            messages=[{"role": "user", "content": "hello"}],
            response_format={"type": "json_object"},
            provider_options={
                "parallel_tool_calls": False,
                "reasoning": {"effort": "medium"},
            },
        )
    finally:
        await backend.close()

    assert result.content == "done"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["parallel_tool_calls"] is False
    assert payload["reasoning"] == {"effort": "medium"}


@pytest.mark.asyncio
async def test_openai_compatible_backend_streaming_requests_assemble_completion() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        chunks = [
            {"choices": [{"delta": {"content": "Thinking "}}]},
            {"choices": [{"delta": {"content": "done"}}]},
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call-1",
                                    "function": {
                                        "name": "file_read",
                                        "arguments": '{"file_path":"x.txt"}',
                                    },
                                }
                            ]
                        }
                    }
                ]
            },
            {"usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}},
        ]
        body = "\n".join([*(f"data: {json.dumps(chunk)}" for chunk in chunks), "data: [DONE]"])
        return httpx.Response(200, text=body)

    backend = OpenAICompatibleAgentBackend(
        base_url="http://provider.test",
        api_key="provider-token",
        model="gpt-test",
        request_timeout=10.0,
    )
    backend._client = httpx.AsyncClient(
        base_url="http://provider.test",
        headers={"Authorization": "Bearer provider-token"},
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
    assert result.content == "Thinking done"
    assert result.tool_calls == [
        {
            "id": "call-1",
            "type": "function",
            "function": {"name": "file_read", "arguments": '{"file_path":"x.txt"}'},
        }
    ]
    assert result.usage == {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}


@pytest.mark.asyncio
async def test_openai_compatible_backend_supports_path_prefixed_base_urls() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "done", "tool_calls": []}}],
                "usage": {"total_tokens": 3},
            },
        )

    backend = OpenAICompatibleAgentBackend(
        base_url="https://openrouter.ai/api",
        api_key="openrouter-token",
        model="anthropic/claude-sonnet-4",
        request_timeout=10.0,
    )
    backend._client = httpx.AsyncClient(
        base_url="https://openrouter.ai/api/",
        headers={"Authorization": "Bearer openrouter-token"},
        transport=httpx.MockTransport(handler),
    )

    try:
        result = await backend.complete(
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
        )
    finally:
        await backend.close()

    assert result.content == "done"
    assert captured["path"] == "/api/v1/chat/completions"


@pytest.mark.asyncio
async def test_anthropic_backend_posts_messages_payload_and_normalizes_tool_use() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "done"},
                    {
                        "type": "tool_use",
                        "id": "call-1",
                        "name": "file_read",
                        "input": {"file_path": "x.txt"},
                    },
                ],
                "usage": {"input_tokens": 3, "output_tokens": 4},
            },
        )

    backend = AnthropicMessagesAgentBackend(
        base_url="https://api.anthropic.com",
        api_key="anthropic-token",
        model="claude-sonnet-4-20250514",
        max_tokens=512,
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
            messages=[
                {"role": "system", "content": "You are a coding agent."},
                {"role": "user", "content": "hello"},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "file_read",
                        "description": "Read a file.",
                        "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}},
                    },
                }
            ],
        )
    finally:
        await backend.close()

    assert result.content == "done"
    assert result.tool_calls[0]["function"]["name"] == "file_read"
    assert result.tool_calls[0]["function"]["arguments"] == json.dumps({"file_path": "x.txt"})
    assert result.usage == {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}
    assert captured["path"] == "/v1/messages"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers.get("x-api-key") == "anthropic-token"
    assert headers.get("anthropic-version") == "2023-06-01"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "claude-sonnet-4-20250514"
    assert payload["system"] == "You are a coding agent."
    assert payload["messages"][0]["content"] == "hello"
    assert payload["tools"][0]["name"] == "file_read"


@pytest.mark.asyncio
async def test_anthropic_backend_forwards_provider_options() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "done"}],
                "usage": {"input_tokens": 2, "output_tokens": 1},
            },
        )

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
            provider_options={
                "metadata": {"source": "agent"},
                "thinking": {"type": "enabled", "budget_tokens": 128},
            },
        )
    finally:
        await backend.close()

    assert result.content == "done"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["metadata"] == {"source": "agent"}
    assert payload["thinking"] == {"type": "enabled", "budget_tokens": 128}


@pytest.mark.asyncio
async def test_anthropic_backend_normalizes_openai_image_url_blocks() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "done"}],
                "usage": {"input_tokens": 2, "output_tokens": 1},
            },
        )

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
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "inspect this"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,iVBORw0KGgo="},
                        },
                    ],
                }
            ],
        )
    finally:
        await backend.close()

    assert result.content == "done"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    content = payload["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "inspect this"}
    assert content[1] == {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "iVBORw0KGgo=",
        },
    }


@pytest.mark.asyncio
async def test_anthropic_backend_rejects_structured_output_requests() -> None:
    backend = AnthropicMessagesAgentBackend(
        base_url="https://api.anthropic.com",
        api_key="anthropic-token",
        model="claude-sonnet-4-20250514",
    )

    with pytest.raises(ValueError, match="Structured response_format is not yet exposed"):
        await backend.complete(
            messages=[{"role": "user", "content": "hello"}],
            response_format={"type": "json_object"},
        )


def test_build_agent_backend_selects_openai_compatible_backend() -> None:
    config = BeepConfig(
        agent_backend="openai-compatible",
        agent_base_url="http://provider.test",
        agent_api_key="provider-token",
        agent_model="model-x",
    )
    backend = build_agent_backend(config)
    assert isinstance(backend, OpenAICompatibleAgentBackend)


def test_build_agent_backend_selects_openai_backend_with_hosted_defaults() -> None:
    config = BeepConfig(
        agent_backend="openai",
        agent_api_key="openai-token",
        agent_model="gpt-4.1-mini",
    )

    backend = build_agent_backend(config)

    assert isinstance(backend, OpenAICompatibleAgentBackend)
    assert backend._base_url == "https://api.openai.com"
    assert backend._api_key == "openai-token"
    assert backend._model == "gpt-4.1-mini"


def test_build_agent_backend_selects_anthropic_backend_with_hosted_defaults() -> None:
    config = BeepConfig(
        agent_backend="anthropic",
        agent_api_key="anthropic-token",
        agent_model="claude-sonnet-4-20250514",
    )

    backend = build_agent_backend(config)

    assert isinstance(backend, AnthropicMessagesAgentBackend)
    assert backend._base_url == "https://api.anthropic.com"
    assert backend._api_key == "anthropic-token"
    assert backend._model == "claude-sonnet-4-20250514"


def test_build_agent_backend_selects_openrouter_backend_with_hosted_defaults() -> None:
    config = BeepConfig(
        agent_backend="openrouter",
        agent_api_key="openrouter-token",
        agent_model="anthropic/claude-sonnet-4",
    )

    backend = build_agent_backend(config)

    assert isinstance(backend, OpenAICompatibleAgentBackend)
    assert backend._base_url == "https://openrouter.ai/api"
    assert backend._api_key == "openrouter-token"
    assert backend._model == "anthropic/claude-sonnet-4"


def test_build_agent_backend_selects_lm_studio_backend_with_local_defaults() -> None:
    config = BeepConfig(agent_backend="lm-studio", agent_model="qwen-coder")

    backend = build_agent_backend(config)

    assert isinstance(backend, OpenAICompatibleAgentBackend)
    assert backend._base_url == "http://localhost:1234"
    assert backend._api_key is None
    assert backend._model == "qwen-coder"


def test_build_agent_backend_selects_ollama_backend_with_local_defaults() -> None:
    config = BeepConfig(agent_backend="ollama", agent_model="qwen2.5-coder")

    backend = build_agent_backend(config)

    assert isinstance(backend, OpenAICompatibleAgentBackend)
    assert backend._base_url == "http://localhost:11434"
    assert backend._api_key is None
    assert backend._model == "qwen2.5-coder"


def test_build_agent_backend_uses_beep_backend_by_default() -> None:
    config = BeepConfig(server_url="http://localhost:5000", api_token="token")
    client = MagicMock()
    backend = build_agent_backend(config, client=client, coding_assistant={"project_id": 1})
    assert isinstance(backend, BeepAgentBackend)


def test_provider_registry_lists_builtin_backends() -> None:
    providers = {provider.key for provider in list_agent_backend_providers()}

    assert providers == {"anthropic", "beep", "openai", "openai-compatible", "openrouter", "lm-studio", "ollama"}


def test_provider_registry_returns_anthropic_provider() -> None:
    provider = get_agent_backend_provider("anthropic")

    assert provider.key == "anthropic"
    assert provider.is_configured(
        BeepConfig(
            agent_backend="anthropic",
            agent_api_key="anthropic-token",
            agent_model="claude-sonnet-4-20250514",
        )
    ) is True
    assert provider.is_configured(
        BeepConfig(agent_backend="anthropic", agent_api_key="anthropic-token")
    ) is False


def test_provider_registry_returns_openai_provider() -> None:
    provider = get_agent_backend_provider("openai")

    assert provider.key == "openai"
    assert provider.is_configured(
        BeepConfig(
            agent_backend="openai",
            agent_api_key="openai-token",
            agent_model="gpt-4.1-mini",
        )
    ) is True
    assert provider.is_configured(BeepConfig(agent_backend="openai", agent_api_key="openai-token")) is False


def test_provider_registry_returns_openrouter_provider() -> None:
    provider = get_agent_backend_provider("openrouter")

    assert provider.key == "openrouter"
    assert provider.is_configured(
        BeepConfig(
            agent_backend="openrouter",
            agent_api_key="openrouter-token",
            agent_model="anthropic/claude-sonnet-4",
        )
    ) is True
    assert provider.is_configured(
        BeepConfig(agent_backend="openrouter", agent_api_key="openrouter-token")
    ) is False


def test_provider_registry_returns_openai_compatible_provider() -> None:
    provider = get_agent_backend_provider("openai-compatible")

    assert provider.key == "openai-compatible"


def test_provider_registry_returns_lm_studio_provider() -> None:
    provider = get_agent_backend_provider("lm-studio")

    assert provider.key == "lm-studio"
    assert provider.is_configured(BeepConfig(agent_backend="lm-studio", agent_model="qwen-coder")) is True
    assert provider.is_configured(BeepConfig(agent_backend="lm-studio")) is False


def test_provider_registry_returns_ollama_provider() -> None:
    provider = get_agent_backend_provider("ollama")

    assert provider.key == "ollama"
    assert provider.is_configured(BeepConfig(agent_backend="ollama", agent_model="qwen2.5-coder")) is True
    assert provider.is_configured(BeepConfig(agent_backend="ollama")) is False


@pytest.mark.asyncio
async def test_probe_agent_backend_configuration_validates_openai_selected_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "model-x"}, {"id": "model-y"}]})

    client = httpx.AsyncClient(
        base_url="http://provider.test",
        transport=httpx.MockTransport(handler),
    )
    config = BeepConfig(
        agent_backend="openai-compatible",
        agent_base_url="http://provider.test",
        agent_api_key="provider-token",
        agent_model="model-x",
    )

    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "beep.agent.provider_plugins.httpx.AsyncClient",
                lambda *args, **kwargs: client,
            )
            result = await probe_agent_backend_configuration(config)
    finally:
        await client.aclose()

    assert isinstance(result, ProviderProbeResult)
    assert result.supported is True
    assert result.success is True
    assert "model-x" in result.message


@pytest.mark.asyncio
async def test_probe_agent_backend_configuration_reports_missing_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "model-a"}]})

    client = httpx.AsyncClient(
        base_url="http://provider.test",
        transport=httpx.MockTransport(handler),
    )
    config = BeepConfig(
        agent_backend="openai-compatible",
        agent_base_url="http://provider.test",
        agent_api_key="provider-token",
        agent_model="model-x",
    )

    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "beep.agent.provider_plugins.httpx.AsyncClient",
                lambda *args, **kwargs: client,
            )
            result = await probe_agent_backend_configuration(config)
    finally:
        await client.aclose()

    assert result.supported is True
    assert result.success is False
    assert "model-x" in result.message


@pytest.mark.asyncio
async def test_probe_agent_backend_configuration_uses_runtime_plugin_probe() -> None:
    config = BeepConfig(agent_backend="custom-provider", agent_model="model-x")
    provider = SimpleNamespace(
        probe_configuration=lambda cfg: ProviderProbeResult(
            supported=True,
            success=True,
            message=f"Plugin probe accepted {cfg.agent_model}.",
        )
    )
    registry = SimpleNamespace(
        get_backend_provider=lambda key: provider if key == "custom-provider" else None,
    )

    result = await probe_agent_backend_configuration(config, plugin_registry=registry)

    assert result.supported is True
    assert result.success is True
    assert "model-x" in result.message


@pytest.mark.asyncio
async def test_probe_agent_backend_configuration_validates_anthropic_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "claude-sonnet-4-20250514"
        assert payload["max_tokens"] == 1
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    client = httpx.AsyncClient(
        base_url="https://api.anthropic.com",
        transport=httpx.MockTransport(handler),
    )
    config = BeepConfig(
        agent_backend="anthropic",
        agent_api_key="anthropic-token",
        agent_model="claude-sonnet-4-20250514",
    )

    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "beep.agent.provider_builtin_anthropic.httpx.AsyncClient",
                lambda *args, **kwargs: client,
            )
            result = await probe_agent_backend_configuration(config)
    finally:
        await client.aclose()

    assert result.supported is True
    assert result.success is True
    assert "claude-sonnet-4-20250514" in result.message


@pytest.mark.asyncio
async def test_probe_agent_backend_configuration_validates_openrouter_provider_with_path_prefix() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/models"
        return httpx.Response(200, json={"data": [{"id": "anthropic/claude-sonnet-4"}]})

    client = httpx.AsyncClient(
        base_url="https://openrouter.ai/api/",
        transport=httpx.MockTransport(handler),
    )
    config = BeepConfig(
        agent_backend="openrouter",
        agent_api_key="openrouter-token",
        agent_model="anthropic/claude-sonnet-4",
    )

    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "beep.agent.provider_base.httpx.AsyncClient",
                lambda *args, **kwargs: client,
            )
            result = await probe_agent_backend_configuration(config)
    finally:
        await client.aclose()

    assert result.supported is True
    assert result.success is True
    assert "anthropic/claude-sonnet-4" in result.message


def test_build_agent_backend_uses_runtime_plugin_provider() -> None:
    config = BeepConfig(agent_backend="custom-provider")
    backend = MagicMock()
    provider = SimpleNamespace(
        build_backend=lambda cfg, *, client=None, coding_assistant=None: backend,
        describe=lambda cfg: None,
        is_configured=lambda cfg: True,
    )
    registry = SimpleNamespace(get_backend_provider=lambda key: provider if key == "custom-provider" else None)

    resolved = build_agent_backend(config, plugin_registry=registry)

    assert resolved is backend