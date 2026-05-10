"""Async API client for Beep.AI.Server.

Beep.AI.Code connects to Beep.AI.Server the same way Claude Code connects to
Anthropic's API or Codex CLI connects to OpenAI's API — via token-authenticated
endpoints.

External API surface (token-auth):
- /v1/chat/completions  — OpenAI-compatible (llm:write)
- /v1/models            — List/get models (llm:read)
- /v1/messages          — Anthropic-compatible (llm:write)
- /v1/responses         — OpenAI Responses API (llm:write)
- /v1/embeddings        — Embedding generation (llm:read)
- /ai-middleware/api/agents/bundles/import — Portable bundle registration/import (agent:*)
- /ai-middleware/api/coding-assistant/* — Workspace/project/session bootstrap

Internal API surface (website session auth, NOT for CLI):
- /coding-assistant/*   — Web UI only
- /dashboard/*          — Web UI only
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from beep.api.errors import BeepAPIError
from beep.api.client_agent_bundle_support import BeepAPIClientAgentBundleMixin
from beep.api.client_llm_support import BeepAPIClientLLMMixin
from beep.api.client_workspace_support import BeepAPIClientWorkspaceMixin
from beep.config import BeepConfig


class BeepAPIClient(
    BeepAPIClientLLMMixin,
    BeepAPIClientWorkspaceMixin,
    BeepAPIClientAgentBundleMixin,
):
    """Async HTTP client for Beep.AI.Server external APIs."""

    def __init__(self, config: BeepConfig) -> None:
        self._config = config
        self._base_url = config.server_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._last_stream_usage: dict[str, int] | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self._config.api_token:
                headers["Authorization"] = f"Bearer {self._config.api_token}"
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=httpx.Timeout(self._config.request_timeout, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generic HTTP request with typed error wrapping and retry on 429/503."""
        client = await self._get_client()
        max_attempts = (self._config.max_retries + 1) if self._config.retry_on_429 else 1

        for attempt in range(max_attempts):
            try:
                response = await client.request(
                    method, path, json=json, params=params, headers=extra_headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                # Retry on 429 Too Many Requests and 503 Service Unavailable
                if (
                    self._config.retry_on_429
                    and status in (429, 503)
                    and attempt < max_attempts - 1
                ):
                    backoff = 2 ** attempt  # 1 s, 2 s, 4 s …
                    await asyncio.sleep(backoff)
                    continue
                try:
                    server_message = exc.response.text
                except Exception:
                    server_message = str(exc)
                raise BeepAPIError(status, path, server_message) from exc

        # Unreachable — loop always returns or raises.
        raise BeepAPIError(0, path, "Unexpected request failure")
