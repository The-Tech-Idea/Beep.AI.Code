"""Search commands: /rag, /collections."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command



from beep.utils.console import get_console
class RagCommand(Command):
    @property
    def name(self) -> str:
        return "rag"

    @property
    def description(self) -> str:
        return "Semantic code search"

    @property
    def category(self) -> str:
        return "Search"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /rag <query>[/yellow]")
            return
        from beep.rag.client import RAGClient
        from beep.rag.search import display_search_results, semantic_search

        rag = RAGClient(ctx["client"])
        results = await semantic_search(rag, args)
        display_search_results(results)


class CollectionsCommand(Command):
    @property
    def name(self) -> str:
        return "collections"

    @property
    def description(self) -> str:
        return "List RAG collections"

    @property
    def category(self) -> str:
        return "Search"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        from beep.rag.client import RAGClient
        from beep.rag.collections import list_collections

        rag = RAGClient(ctx["client"])
        await list_collections(rag)
