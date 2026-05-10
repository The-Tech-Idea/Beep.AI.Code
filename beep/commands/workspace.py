"""Workspace commands: tree, cat, grep."""

from __future__ import annotations

from pathlib import Path

import typer

from beep.workspace.search import search_workspace
from beep.workspace.view import read_workspace_file, show_workspace_tree
from beep.utils.console import get_console



def tree_cmd(
    path: str = typer.Argument(".", help="Directory to show"),
    depth: int = typer.Option(3, "--depth", "-d", help="Maximum depth"),
    all_files: bool = typer.Option(False, "--all", "-a", help="Show ignored files"),
) -> None:
    """Display workspace file tree."""
    try:
        show_workspace_tree(path, max_depth=depth, show_all=all_files)
    except (ValueError, RuntimeError) as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


def cat_cmd(
    path: str = typer.Argument(..., help="File to display"),
    start: int = typer.Option(None, "--start", "-s", help="Start line"),
    end: int = typer.Option(None, "--end", "-e", help="End line"),
    no_numbers: bool = typer.Option(False, "--no-numbers", help="Hide line numbers"),
    no_highlight: bool = typer.Option(False, "--raw", help="Disable syntax highlighting"),
) -> None:
    """Display file content with syntax highlighting."""
    try:
        content = read_workspace_file(
            path,
            start_line=start,
            end_line=end,
            show_numbers=not no_numbers,
            highlight=not no_highlight,
        )
    except (ValueError, RuntimeError) as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    get_console().print(content)


def grep_cmd(
    pattern: str = typer.Argument(..., help="Search pattern"),
    path: str = typer.Argument(".", help="Directory to search"),
    case_sensitive: bool = typer.Option(
        False, "-C", "--case-sensitive", help="Case sensitive search",
    ),
    file_pattern: str = typer.Option(None, "--name", "-n", help="File glob pattern"),
) -> None:
    """Search files for a pattern."""
    root = Path(path).resolve()
    normalized_file_pattern = file_pattern if isinstance(file_pattern, str) else None
    if not root.is_dir():
        get_console().print(f"[red]Not a directory: {path}[/red]")
        raise typer.Exit(1)

    try:
        result = search_workspace(
            root,
            pattern=pattern,
            case_sensitive=case_sensitive,
            file_pattern=normalized_file_pattern,
        )
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    for match in result.matches:
        get_console().print(
            f"[cyan]{match.relative_path}[/cyan]:[green]{match.line_number}[/green]: {match.line_text}"
        )

    if not result.matches:
        get_console().print("[yellow]No matches found[/yellow]")
