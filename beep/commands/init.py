"""beep init — scaffold project memory, rules, and configuration."""

from __future__ import annotations

import typer

from beep.onboarding.scaffold import ProjectScaffold
from beep.utils.console import get_console
from beep.workspace.detector import find_workspace_root


def init_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
) -> None:
    """Initialize Beep.AI.Code for this project.

    Creates:
      .beep.md             — Project memory (tech stack, conventions)
      .beep/rules.md       — AI assistant rules and coding standards
      .beep/ignore         — Files/directories to exclude from context
      .beep/commands.md    — Custom slash command definitions

    Existing files are preserved unless --force is used.
    """
    root = find_workspace_root()
    scaffold = ProjectScaffold(root)
    result = scaffold.scaffold(force=force)

    get_console().print(f"\n[bold]Initializing Beep.AI in '{root.name}'...[/bold]\n")

    for path in result.created:
        get_console().print(f"  [green]+[/green] {path}")
    for path in result.skipped:
        get_console().print(f"  [dim]~[/dim] {path} [dim](exists, use --force to overwrite)[/dim]")

    if not result.created and not result.skipped:
        get_console().print("  [dim](nothing to do)[/dim]")

    get_console().print(
        "\n[dim]Loaders will now pick up .beep.md, .beep/rules.md, "
        "and .beep/commands.md on the next session start.[/dim]"
    )

    if result.created:
        get_console().print(
            "\n[green]Done![/green] Start a new chat session to use the scaffolded files."
        )
