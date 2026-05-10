"""Tests for API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from beep.api.client import BeepAPIClient
from beep.api.errors import BeepAPIError
from beep.config import BeepConfig


def _ok_response(payload: dict) -> MagicMock:
    """Build a mock response that raise_for_status passes and returns payload."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status_code: int, body: str = "") -> MagicMock:
    """Build a mock response that raise_for_status raises HTTPStatusError."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = body
    request = httpx.Request("GET", "http://test/path")
    exc = httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=resp
    )
    resp.raise_for_status = MagicMock(side_effect=exc)
    return resp


class TestBeepAPIClient:
    def test_init(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
        )
        client = BeepAPIClient(config)
        assert client._base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=_ok_response({"status": "ok"}))
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            result = await client.health_check()
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(Exception, match="Connection refused"):
                await client.health_check()

    @pytest.mark.asyncio
    async def test_chat_completion(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_ok_response({
                "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
                "usage": {"total_tokens": 15},
            })
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )
            assert "choices" in result

    def test_base_url_stripped(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000/",
            api_token="test-token",
        )
        client = BeepAPIClient(config)
        assert client._base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
        )
        client = BeepAPIClient(config)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.aclose = AsyncMock()

        client._client = mock_httpx
        await client.close()
        mock_httpx.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_list_models(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_ok_response({"data": [{"id": "gpt-4"}, {"id": "gpt-3.5"}]})
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            models = await client.list_models()
            assert len(models) == 2
            assert models[0]["id"] == "gpt-4"


class TestBeepAPIError:
    def test_has_status_code_and_message(self) -> None:
        err = BeepAPIError(404, "/v1/models", "not found")
        assert err.status_code == 404
        assert err.endpoint == "/v1/models"
        assert err.server_message == "not found"
        assert "404" in str(err)
        assert "/v1/models" in str(err)
        assert "not found" in str(err)

    def test_is_exception_subclass(self) -> None:
        err = BeepAPIError(500, "/api/health", "internal server error")
        assert isinstance(err, Exception)


class TestRequestMethod:
    @pytest.mark.asyncio
    async def test_request_raises_beep_api_error_on_404(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
            retry_on_429=False,
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_error_response(404, "not found")
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(BeepAPIError) as exc_info:
                await client._request("GET", "/v1/models")
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_request_does_not_retry_non_429(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
            retry_on_429=True,
            max_retries=3,
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_error_response(500, "server error")
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(BeepAPIError) as exc_info:
                await client._request("GET", "/v1/models")
            # Should NOT retry on 500 — only one attempt
            assert mock_client.request.await_count == 1
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_request_retries_on_429_then_succeeds(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
            retry_on_429=True,
            max_retries=3,
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            side_effect=[
                _error_response(429, "rate limited"),
                _error_response(429, "rate limited"),
                _ok_response({"data": [{"id": "model-1"}]}),
            ]
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await client._request("GET", "/v1/models")

        assert result == {"data": [{"id": "model-1"}]}
        assert mock_client.request.await_count == 3
        assert mock_sleep.await_count == 2

    @pytest.mark.asyncio
    async def test_request_exhausts_retries_on_429(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
            retry_on_429=True,
            max_retries=2,
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_error_response(429, "still rate limited")
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(BeepAPIError) as exc_info:
                    await client._request("GET", "/v1/models")

        assert exc_info.value.status_code == 429
        # max_retries=2 means 3 total attempts
        assert mock_client.request.await_count == 3

    @pytest.mark.asyncio
    async def test_request_no_retry_when_retry_on_429_false(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
            retry_on_429=False,
            max_retries=3,
        )
        client = BeepAPIClient(config)

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value=_error_response(429, "rate limited")
        )
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(BeepAPIError):
                await client._request("GET", "/v1/models")
        assert mock_client.request.await_count == 1

    @pytest.mark.asyncio
    async def test_get_client_uses_request_timeout_from_config(self) -> None:
        config = BeepConfig(
            server_url="http://localhost:8000",
            api_token="test-token",
            request_timeout=45.0,
        )
        client = BeepAPIClient(config)
        # Trigger client creation
        httpx_client = await client._get_client()
        try:
            assert httpx_client.timeout.read == 45.0
        finally:
            await client.close()

