"""Web search CLI command."""

from __future__ import annotations

import asyncio

import typer

from beep.utils.console import get_console
from beep.websearch.service import WebSearchService


def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
) -> None:
    """Search the web. Requires BEEP_WEBSEARCH=1."""

    async def _run() -> None:
        service = WebSearchService()
        results = await service.search(query, num_results=5)
        if not results:
            get_console().print("[yellow]No results[/yellow]")
            return
        for i, r in enumerate(results, 1):
            get_console().print(f"\n[bold]{i}. {r.title}[/bold]")
            if r.url:
                get_console().print(f"   [dim]{r.url}[/dim]")
            if r.snippet:
                get_console().print(f"   {r.snippet}")

    asyncio.run(_run())
