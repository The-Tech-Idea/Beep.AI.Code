"""Session management commands."""

from __future__ import annotations

from pathlib import Path

import typer

from beep.sessions.export import export_json, export_markdown
from beep.sessions.history import list_sessions
from beep.sessions.presentation import build_sessions_table
from beep.utils.console import get_console



def sessions_list_cmd() -> None:
    """List all saved sessions."""
    try:
        sessions = list_sessions()
        if not sessions:
            get_console().print("[yellow]No sessions found[/yellow]")
            return
        get_console().print(build_sessions_table(sessions, title="Saved Sessions"))
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def sessions_export_cmd(
    session_id: str = typer.Argument(..., help="Session ID to export"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("markdown", "--format", "-f", help="Export format: markdown, json"),
) -> None:
    """Export a session to a file."""
    output_path = Path(output) if output else None
    normalized_format = (format or "").strip().lower()
    if normalized_format not in {"markdown", "json"}:
        get_console().print("[red]Invalid format. Use 'markdown' or 'json'.[/red]")
        raise typer.Exit(1)

    try:
        if normalized_format == "json":
            path = export_json(session_id, output_path)
        else:
            path = export_markdown(session_id, output_path)
        get_console().print(f"[green]Exported session to {path}[/green]")
    except ValueError as e:
        get_console().print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def sessions_delete_cmd(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
) -> None:
    """Delete a saved session."""
    from beep.sessions.history import delete_session

    try:
        if delete_session(session_id):
            get_console().print(f"[green]Deleted session {session_id}[/green]")
        else:
            get_console().print(f"[red]Session not found: {session_id}[/red]")
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
