"""Tests for extended API client methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.api.client import BeepAPIClient
from beep.config import BeepConfig


def _make_mock_response(data: dict) -> MagicMock:
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def client() -> BeepAPIClient:
    """Create a test API client."""
    config = BeepConfig(
        server_url="http://localhost:8000",
        api_token="test-token",
    )
    return BeepAPIClient(config)


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(return_value=_make_mock_response({"status": "ok"}))
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.health_check()
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_v1_health(self, client: BeepAPIClient) -> None:
        """v1_health hits /v1/health and returns coding_model_tiers."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {
                    "status": "ok",
                    "coding_model_tiers": {
                        "fast": "coding-fast",
                        "balanced": "coding-balanced",
                        "powerful": "coding-powerful",
                    },
                }
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.v1_health()
            assert result["status"] == "ok"
            assert "coding_model_tiers" in result
            call_args = mock_httpx.request.call_args
            assert call_args.args[0] == "GET"
            assert "/v1/health" in call_args.args[1]


class TestModelsAPI:
    @pytest.mark.asyncio
    async def test_list_models(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(return_value=_make_mock_response({"data": [{"id": "gpt-4"}]}))
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.list_models()
            assert len(result) == 1
            assert result[0]["id"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_get_model(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(return_value=_make_mock_response({"id": "gpt-4"}))
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.get_model("gpt-4")
            assert result["id"] == "gpt-4"


class TestChatCompletion:
    @pytest.mark.asyncio
    async def test_chat_completion(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {
                    "choices": [{"message": {"content": "hello"}}],
                }
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
            )
            assert result["choices"][0]["message"]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_chat_with_coding_metadata(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {
                    "choices": [{"message": {"content": "done"}}],
                    "coding_assistant": {"project_id": 1, "session_id": "s1"},
                }
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "fix bug"}],
                coding_assistant={"project_id": 1, "interaction_mode": "agent"},
            )
            assert "coding_assistant" in result
            assert result["coding_assistant"]["project_id"] == 1

    @pytest.mark.asyncio
    async def test_chat_completion_forwards_response_format(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {
                    "choices": [{"message": {"content": "done"}}],
                }
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                response_format={"type": "json_object"},
            )
            assert result["choices"][0]["message"]["content"] == "done"
            _, kwargs = mock_httpx.request.call_args
            assert kwargs["json"]["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_stream_usage_is_captured(self, client: BeepAPIClient) -> None:
        class _StreamContext:
            def __init__(self, lines: list[str]) -> None:
                self._lines = lines

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self) -> None:
                return None

            async def aiter_lines(self):
                for line in self._lines:
                    yield line

        lines = [
            'data: {"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}',
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            "data: [DONE]",
        ]
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=_StreamContext(lines))
        with patch.object(client, "_get_client", return_value=mock_httpx):
            chunks = []
            async for chunk in client.chat_completion_stream(
                messages=[{"role": "user", "content": "hi"}]
            ):
                chunks.append(chunk)
            assert "".join(chunks) == "Hello"
            usage = client.get_last_stream_usage()
            assert usage is not None
            assert usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_chat_completion_event_stream_yields_tool_call_deltas(self, client: BeepAPIClient) -> None:
        class _StreamContext:
            def __init__(self, lines: list[str]) -> None:
                self._lines = lines

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self) -> None:
                return None

            async def aiter_lines(self):
                for line in self._lines:
                    yield line

        lines = [
            'data: {"choices":[{"delta":{"content":"Hello","tool_calls":[{"index":0,"id":"call-1","function":{"name":"file_read","arguments":"{}"}}]}}]}',
            'data: {"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}',
            "data: [DONE]",
        ]
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=_StreamContext(lines))
        with patch.object(client, "_get_client", return_value=mock_httpx):
            events = []
            async for event in client.chat_completion_event_stream(
                messages=[{"role": "user", "content": "hi"}]
            ):
                events.append(event)

        assert events[0].content == "Hello"
        assert events[0].tool_calls[0].name == "file_read"
        assert events[-1].usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


class TestAnthropicAPI:
    @pytest.mark.asyncio
    async def test_anthropic_messages(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"content": [{"text": "hi"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.anthropic_messages([{"role": "user", "content": "hi"}])
            assert "content" in result

    @pytest.mark.asyncio
    async def test_anthropic_messages_with_tools_and_system(self, client: BeepAPIClient) -> None:
        """tools and system are included in the request body."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"content": [{"text": "done"}]})
        )
        tools = [{"name": "bash", "description": "run shell", "input_schema": {"type": "object"}}]
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.anthropic_messages(
                [{"role": "user", "content": "run it"}],
                system="You are a coding agent.",
                tools=tools,
            )
            assert "content" in result
            _, kwargs = mock_httpx.request.call_args
            body = kwargs["json"]
            assert body["system"] == "You are a coding agent."
            assert body["tools"] == tools

    @pytest.mark.asyncio
    async def test_anthropic_messages_with_thinking(self, client: BeepAPIClient) -> None:
        """thinking config is forwarded in the payload."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"content": [{"type": "thinking", "thinking": "..."}]})
        )
        thinking = {"type": "enabled", "budget_tokens": 8000}
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.anthropic_messages(
                [{"role": "user", "content": "think hard"}],
                thinking=thinking,
            )
            assert "content" in result
            _, kwargs = mock_httpx.request.call_args
            body = kwargs["json"]
            assert body["thinking"] == thinking

    @pytest.mark.asyncio
    async def test_anthropic_messages_with_beta_features(self, client: BeepAPIClient) -> None:
        """beta_features are joined and sent as the anthropic-beta request header."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"content": [{"text": "ok"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            await client.anthropic_messages(
                [{"role": "user", "content": "hi"}],
                beta_features=["interleaved-thinking-2025-05-14", "prompt-caching-2024-07-31"],
            )
            _, kwargs = mock_httpx.request.call_args
            sent_headers = kwargs.get("headers") or {}
            assert sent_headers.get("anthropic-beta") == (
                "interleaved-thinking-2025-05-14,prompt-caching-2024-07-31"
            )

    @pytest.mark.asyncio
    async def test_anthropic_messages_no_beta_features_sends_no_header(self, client: BeepAPIClient) -> None:
        """When beta_features is empty/None no anthropic-beta header is injected."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"content": [{"text": "ok"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            await client.anthropic_messages([{"role": "user", "content": "hi"}])
            _, kwargs = mock_httpx.request.call_args
            sent_headers = kwargs.get("headers")
            assert sent_headers is None


class TestExtendedOpenAIAPI:
    @pytest.mark.asyncio
    async def test_responses_completion(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"output": [{"type": "message"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.responses_completion("hello")
            assert "output" in result

    @pytest.mark.asyncio
    async def test_openai_responses_string_input(self, client: BeepAPIClient) -> None:
        """openai_responses works with a plain string input."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"output": [{"type": "message"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.openai_responses("hello")
            assert "output" in result
            _, kwargs = mock_httpx.request.call_args
            assert kwargs["json"]["input"] == "hello"

    @pytest.mark.asyncio
    async def test_openai_responses_list_input(self, client: BeepAPIClient) -> None:
        """openai_responses accepts a list of input item dicts."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"output": [{"type": "message"}]})
        )
        items = [{"type": "message", "role": "user", "content": "hi"}]
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.openai_responses(items)
            assert "output" in result
            _, kwargs = mock_httpx.request.call_args
            assert kwargs["json"]["input"] == items

    @pytest.mark.asyncio
    async def test_openai_responses_with_previous_response_id(self, client: BeepAPIClient) -> None:
        """previous_response_id is forwarded in the payload."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"output": [{"type": "message"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            await client.openai_responses(
                "continue", previous_response_id="resp_abc123"
            )
            _, kwargs = mock_httpx.request.call_args
            assert kwargs["json"]["previous_response_id"] == "resp_abc123"

    @pytest.mark.asyncio
    async def test_openai_responses_with_reasoning(self, client: BeepAPIClient) -> None:
        """reasoning config is forwarded in the payload."""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"output": [{"type": "reasoning"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            await client.openai_responses("think", reasoning={"effort": "high"})
            _, kwargs = mock_httpx.request.call_args
            assert kwargs["json"]["reasoning"] == {"effort": "high"}

    @pytest.mark.asyncio
    async def test_create_embeddings(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"data": [{"embedding": [0.1]}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.create_embeddings(["hello"])
            assert "data" in result


class TestAIMiddlewareBootstrap:
    """Token-auth coding assistant endpoints for external CLI clients."""

    @pytest.mark.asyncio
    async def test_bootstrap_workspace(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {
                    "success": True,
                    "project_id": 1,
                    "session_id": "s1",
                    "transport": {"base_url": "http://localhost:5000"},
                }
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.bootstrap_workspace("/path/to/project")
            assert result["success"] is True
            assert result["project_id"] == 1

    @pytest.mark.asyncio
    async def test_bootstrap_project(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {
                    "success": True,
                    "session_id": "s1",
                    "transport": {"base_url": "http://localhost:5000"},
                }
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.bootstrap_project(1)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_session(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {
                    "success": True,
                    "session_id": "s1",
                    "transport": {"base_url": "http://localhost:5000"},
                }
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.create_session(1, title="test")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_list_sessions(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response({"sessions": [{"id": "s1"}]})
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.list_sessions(1)
            assert len(result) == 1
            assert result[0]["id"] == "s1"

    @pytest.mark.asyncio
    async def test_compact_conversation(self, client: BeepAPIClient) -> None:
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.request = AsyncMock(
            return_value=_make_mock_response(
                {"messages": [{"role": "system", "content": "summary"}]}
            )
        )
        with patch.object(client, "_get_client", return_value=mock_httpx):
            result = await client.compact_conversation(
                session_id="s1",
                messages=[{"role": "user", "content": "hello"}],
            )
            assert "messages" in result
