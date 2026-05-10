"""Plugin discovery management commands."""

from __future__ import annotations

from pathlib import Path

import typer

from beep.plugins.discovery import add_plugin_search_path
from beep.plugins.runtime import load_runtime_plugins
from beep.workspace.detector import find_workspace_root
from beep.utils.console import get_console



def plugins_paths_cmd() -> None:
    """Show the plugin search paths that Beep.AI.Code scans."""
    workspace_root = find_workspace_root()
    runtime = load_runtime_plugins(workspace_root, enabled=False)

    get_console().print("[bold]Plugin search paths[/bold]")
    for path in runtime.searched_paths:
        get_console().print(f"  - {path}")
    if runtime.discovery_errors:
        get_console().print("\n[yellow]Discovery warnings:[/yellow]")
        for warning in runtime.discovery_errors:
            get_console().print(f"  - {warning}")


def plugins_add_path_cmd(
    path: str = typer.Argument(..., help="Directory to add to plugin discovery"),
    scope: str = typer.Option("workspace", "--scope", help="workspace or user"),
) -> None:
    """Add a file-backed plugin search path manifest entry."""
    workspace_root = find_workspace_root()
    try:
        manifest_path = add_plugin_search_path(workspace_root, Path(path), scope=scope)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except OSError as exc:
        get_console().print(f"[red]Failed to update plugin manifest: {exc}[/red]")
        raise typer.Exit(1)

    get_console().print(f"[green]Updated plugin manifest:[/green] {manifest_path}")