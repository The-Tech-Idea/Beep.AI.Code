"""RAG collection management."""

from __future__ import annotations

from rich.table import Table

from beep.rag.client import RAGClient



from beep.utils.console import get_console
async def list_collections(rag_client: RAGClient) -> None:
    """List all RAG collections."""
    collections = await rag_client.list_collections()

    if not collections:
        get_console().print("[yellow]No collections found[/yellow]")
        return

    table = Table(title="RAG Collections")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Documents", justify="right")
    table.add_column("Description", style="dim")

    for collection in collections:
        table.add_row(
            str(collection.get("id", "")),
            collection.get("name", ""),
            str(collection.get("document_count", 0)),
            collection.get("description", "")[:50],
        )

    get_console().print(table)
