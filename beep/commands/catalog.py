"""Catalog command — browse and search all integration entries."""

from __future__ import annotations

import typer
from rich.table import Table

from beep.integrations.catalog import CURATED_ENTRIES
from beep.integrations.catalog import search as catalog_search
from beep.integrations.installer import is_installed
from beep.utils.console import get_console


def _render_catalog(kind: str | None = None, query: str | None = None) -> None:
    if query:
        entries = catalog_search(query)
        if kind:
            entries = [e for e in entries if e.kind.value == kind]
    else:
        entries = list(CURATED_ENTRIES)
        if kind:
            entries = [e for e in entries if e.kind.value == kind]

    if not entries:
        get_console().print("[dim]No entries found.[/dim]")
        return

    title_parts = ["Catalog"]
    if kind:
        title_parts.append(f"({kind})")
    if query:
        title_parts.append(f"matching '{query}'")

    table = Table(title=" ".join(title_parts))
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Kind", style="magenta")
    table.add_column("Trust", style="yellow")
    table.add_column("Summary", style="dim", max_width=60)
    table.add_column("Status", style="green")

    for entry in entries:
        status = "installed" if is_installed(entry.id) else "-"
        row_style = ""
        if is_installed(entry.id):
            row_style = "green"
        table.add_row(
            entry.id,
            entry.name,
            entry.kind.value,
            entry.trust.value,
            entry.summary,
            status,
            style=row_style,
        )
    get_console().print(table)


def catalog_cmd(
    kind: str | None = typer.Option(
        None, "--kind", "-k", help="Filter by kind: skill, mcp, or tool"
    ),
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
) -> None:
    """Browse and search the integrations catalog."""
    try:
        if kind and kind not in ("skill", "mcp", "tool"):
            get_console().print(f"[red]Invalid kind '{kind}'. Use: skill, mcp, or tool.[/red]")
            raise typer.Exit(1)
        _render_catalog(kind=kind, query=query)
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
