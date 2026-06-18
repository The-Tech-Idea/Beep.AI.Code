"""Web search service — gated wrapper around the search engine."""

from __future__ import annotations

import os

from beep.websearch.search import SearchResult, search_web


class WebSearchService:
    def __init__(self) -> None:
        pass

    def is_enabled(self) -> bool:
        return os.environ.get("BEEP_WEBSEARCH", "").lower() in ("1", "true", "yes")

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        if not self.is_enabled():
            return [
                SearchResult(
                    title="Web search disabled",
                    url="",
                    snippet="Set BEEP_WEBSEARCH=1 to enable web search.",
                )
            ]
        return await search_web(query, num_results=num_results)
