"""Edit command with diff preview."""

from __future__ import annotations

from pathlib import Path

import typer

from beep.workspace.file_ops import apply_edit
from beep.workspace.editing import prepare_workspace_edit
from beep.utils.console import get_console



def edit_cmd(
    path: str = typer.Argument(..., help="File to edit"),
    content: str = typer.Option(None, "--content", "-c", help="New content (or use stdin)"),
    no_confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Edit a file with diff preview.

    Usage:
        beep edit file.py -c "new content"
        echo "new content" | beep edit file.py
    """
    import sys

    file_path = Path(path)
    resolved_content = content if isinstance(content, str) else None
    skip_confirmation = no_confirm if isinstance(no_confirm, bool) else False

    if not file_path.exists():
        if typer.confirm(f"File {path} does not exist. Create it?"):
            file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise typer.Exit(1)

    if resolved_content is None:
        if not sys.stdin.isatty():
            resolved_content = sys.stdin.read()
        else:
            get_console().print("[red]Provide content via --content or pipe[/red]")
            raise typer.Exit(1)

    try:
        prepared_edit = prepare_workspace_edit(file_path, new_content=resolved_content)
    except RuntimeError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    try:
        apply_edit(
            prepared_edit.path,
            prepared_edit.old_content,
            prepared_edit.new_content,
            require_confirm=not skip_confirmation,
        )
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
