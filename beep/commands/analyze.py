"""Analysis commands."""

from __future__ import annotations

import typer

from beep.analysis.stats import analyze_project, display_project_stats
from beep.utils.console import get_console



def analyze_cmd(
    path: str = typer.Argument(".", help="Project path"),
) -> None:
    """Analyze codebase statistics."""
    from pathlib import Path

    workspace_root = Path(path).resolve()
    if not workspace_root.is_dir():
        get_console().print(f"[red]Not a directory: {path}[/red]")
        raise typer.Exit(1)

    try:
        stats = analyze_project(workspace_root)
        display_project_stats(stats)
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
