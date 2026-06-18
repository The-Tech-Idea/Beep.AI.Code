"""Web search slash command for chat."""

from __future__ import annotations

from typing import Any

from beep.chat.commands.base import Command
from beep.utils.console import get_console


class WebSearchCommand(Command):
    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web (requires BEEP_WEBSEARCH=1)"

    @property
    def category(self) -> str:
        return "Search"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /search <query>[/yellow]")
            return

        from beep.websearch.service import WebSearchService

        service = WebSearchService()
        results = await service.search(args, num_results=5)

        if not results:
            get_console().print("[yellow]No results[/yellow]")
            return

        for i, r in enumerate(results, 1):
            get_console().print(f"\n[bold]{i}. {r.title}[/bold]")
            if r.url:
                get_console().print(f"   [dim]{r.url}[/dim]")
            if r.snippet:
                get_console().print(f"   {r.snippet}")
