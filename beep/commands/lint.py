"""Lint commands."""

from __future__ import annotations

import typer

from beep.linter.runner import (
    LinterType,
    detect_linters,
    display_lint_result,
    run_lint,
)
from beep.utils.console import get_console
from beep.cli_support_async import run_async_cmd


def lint_cmd(
    file: str | None = typer.Option(None, "--file", "-f", help="Lint specific file"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues"),
    linter: str | None = typer.Option(None, "--linter", help="Force linter"),
) -> None:
    """Run linter and optionally fix issues."""
    from beep.workspace.detector import find_workspace_root

    workspace_root = find_workspace_root()

    lint_type = None
    if linter:
        try:
            lint_type = LinterType(linter)
        except ValueError:
            get_console().print(f"[red]Unknown linter: {linter}[/red]")
            raise typer.Exit(1)
    else:
        detected = detect_linters(workspace_root)
        names = [lint.value for lint in detected]
        get_console().print(f"[dim]Detected: {', '.join(names) or 'none (using ruff)'}[/dim]")

    async def _run() -> None:
        result = await run_lint(workspace_root, lint_type, file, fix)
        display_lint_result(result)

    run_async_cmd(_run, cancel_message="Lint cancelled")
