"""RAG API client."""

from __future__ import annotations

from typing import Any

from beep.api.client import BeepAPIClient


class RAGClient:
    """Client for RAG operations."""

    def __init__(self, api_client: BeepAPIClient) -> None:
        self._client = api_client

    async def query(
        self,
        query: str,
        collection_id: str | None = None,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Query RAG collections."""
        return await self._client._request(
            "POST",
            "/v1/rag/query",
            json={
                "query": query,
                "collection_id": collection_id,
                "max_results": max_results,
                "return_citations": True,
                "grounded_only": True,
            },
        )

    async def list_collections(self) -> list[dict[str, Any]]:
        """List available RAG collections."""
        result = await self._client._request("GET", "/v1/rag/collections")
        return result.get("collections", [])

    async def augment_messages(
        self,
        messages: list[dict[str, str]],
        collection_ids: list[str] | None = None,
        max_results: int = 5,
    ) -> list[dict[str, str]]:
        """Augment chat messages with RAG context."""
        result = await self._client._request(
            "POST",
            "/v1/rag/augment",
            json={
                "messages": messages,
                "collection_ids": collection_ids,
                "max_results": max_results,
                "return_citations": True,
            },
        )

        context = result.get("context", "")
        if context:
            augmented = list(messages)
            augmented[-1]["content"] = f"{context}\n\n---\n\n{augmented[-1]['content']}"
            return augmented

        return messages
