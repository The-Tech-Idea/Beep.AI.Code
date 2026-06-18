"""Web search tool for the agent — gated, read-only web search."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    read_only_safe = True

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for current information. Returns titles, URLs, and snippets."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "Search query string",
            },
            "num_results": {
                "type": "integer",
                "description": "Maximum results (default 5, max 10)",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["num_results"]

    async def execute(self, *, query: str = "", num_results: int = 5, **kwargs: Any) -> ToolResult:  # noqa: ARG002
        if not query:
            return ToolResult(success=True, output="No search query provided.")

        from beep.app_service import get_app_service

        service = get_app_service().web_search
        results = await service.search(query, num_results=min(num_results, 10))

        if not results:
            return ToolResult(success=True, output="No search results found.")

        lines = [f"Web search results for '{query}':"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. {r.title}")
            if r.url:
                lines.append(f"     {r.url}")
            if r.snippet:
                lines.append(f"     {r.snippet}")

        return ToolResult(success=True, output="\n".join(lines))
