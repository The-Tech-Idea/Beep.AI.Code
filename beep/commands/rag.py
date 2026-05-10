"""RAG commands for semantic search and collection management."""

from __future__ import annotations

import typer

from beep.rag.client import RAGClient
from beep.rag.collections import list_collections
from beep.rag.search import display_search_results, semantic_search
from beep.utils.console import get_console
from beep.cli_support_async import run_async_cmd


def rag_query_cmd(
    query: str = typer.Argument(..., help="Search query"),
    collection: str | None = typer.Option(None, "--collection", "-c", help="Collection ID"),
    max_results: int = typer.Option(5, "--max-results", "-n", help="Maximum results"),
) -> None:
    """Search codebase using semantic search."""
    from beep.app_service import get_app_service
    from beep.setup_wizard import ensure_configured

    config = ensure_configured()

    async def _run() -> None:
        client = get_app_service().api_client(config)
        rag = RAGClient(client)
        results = await semantic_search(rag, query, collection, max_results)
        display_search_results(results)

    run_async_cmd(_run, cancel_message="RAG query cancelled")


def rag_collections_cmd() -> None:
    """List RAG collections."""
    from beep.app_service import get_app_service
    from beep.setup_wizard import ensure_configured

    config = ensure_configured()

    async def _run() -> None:
        client = get_app_service().api_client(config)
        rag = RAGClient(client)
        await list_collections(rag)

    run_async_cmd(_run, cancel_message="RAG collections cancelled")
