"""Semantic code search using RAG."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel

from beep.rag.client import RAGClient



from beep.utils.console import get_console
async def semantic_search(
    rag_client: RAGClient,
    query: str,
    collection_id: str | None = None,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Perform semantic search on codebase.

    Args:
        rag_client: RAG client
        query: Natural language search query
        collection_id: Specific collection to search
        max_results: Maximum results to return

    Returns:
        List of search results with content and metadata
    """
    result = await rag_client.query(query, collection_id, max_results)

    if not result.get("success"):
        get_console().print(f"[red]Search failed: {result.get('error', 'Unknown error')}[/red]")
        return []

    results = result.get("results", [])
    return results


def display_search_results(results: list[dict[str, Any]]) -> None:
    """Display search results with Rich formatting."""
    if not results:
        get_console().print("[yellow]No results found[/yellow]")
        return

    for i, result in enumerate(results, 1):
        content = result.get("content", "")[:300]
        metadata = result.get("metadata", {})
        source = metadata.get("source", "unknown")
        score = result.get("score", 0)

        get_console().print(
            Panel(
                f"[dim]{content}[/dim]\n\n"
                f"Source: [cyan]{source}[/cyan] | "
                f"Relevance: [green]{score:.2%}[/green]",
                title=f"Result {i}",
                border_style="blue",
                padding=(1, 2),
            )
        )
