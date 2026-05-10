"""Template commands."""

from __future__ import annotations

from pathlib import Path

import typer

from beep.templates.generator import (
    display_templates,
    generate_from_template,
    get_template_by_name,
    list_templates,
)
from beep.templates.service import generate_template_file, show_template_listing
from beep.workspace.detector import find_workspace_root
from beep.utils.console import get_console



def template_cmd(
    name: str = typer.Argument(..., help="Template name"),
    output: str = typer.Argument(..., help="Output file path"),
    var: list[str] | None = typer.Option(
        None, "--var", "-v", help="Variable as key=value",
    ),
) -> None:
    """Generate a file from a template."""
    workspace_root = find_workspace_root()
    try:
        result = generate_template_file(
            name=name,
            output_path=Path(output),
            raw_variables=var,
            workspace_root=workspace_root,
            get_template_by_name=get_template_by_name,
            list_templates=list_templates,
            generate_from_template=generate_from_template,
        )
        get_console().print(f"[green]Generated {result}[/green]")
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def template_list_cmd(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
) -> None:
    """List available templates."""
    workspace_root = find_workspace_root()
    try:
        show_template_listing(
            workspace_root=workspace_root,
            category=category,
            list_templates=list_templates,
            display_templates=display_templates,
        )
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
