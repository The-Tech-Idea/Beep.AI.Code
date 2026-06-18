"""First-class git CLI commands — commit, branch, pr, diff, status."""

from __future__ import annotations

from typing import Any

import typer
from typer.models import OptionInfo

from beep.utils.console import get_console
from beep.vcs.workflow import GitWorkflow, GitWorkflowError
from beep.workspace.detector import find_workspace_root


def _coerce(val: Any) -> Any:
    if isinstance(val, OptionInfo):
        return val.default
    return val


def _run_workflow(action_name: str, action) -> None:
    try:
        result = action()
        if result:
            get_console().print(result)
    except GitWorkflowError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


def git_commit_cmd(
    message: str = typer.Option("", "--message", "-m", help="Commit message"),
    all: bool = typer.Option(False, "--all", "-a", help="Stage all changes"),
) -> None:
    """Commit changes to git."""
    message = _coerce(message)
    all = _coerce(all)
    root = find_workspace_root()
    wf = GitWorkflow(root)
    try:
        wf.ensure_repo()
    except GitWorkflowError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if not message:
        get_console().print('[yellow]Commit message required. Use -m "message"[/yellow]')
        raise typer.Exit(1)

    if wf.commit(str(message), all_changes=bool(all)):
        get_console().print(f"[green]Committed: {message}[/green]")


def git_diff_cmd(
    staged: bool = typer.Option(False, "--staged", "-s", help="Show staged changes"),
    file: str | None = typer.Option(None, "--file", "-f", help="Show diff for specific file"),
) -> None:
    """Show git diff."""
    staged = _coerce(staged)
    file = _coerce(file)
    root = find_workspace_root()
    wf = GitWorkflow(root)
    _run_workflow("diff", lambda: wf.diff(staged=bool(staged), file_path=file))


def git_branch_cmd(
    name: str = typer.Argument(..., help="Branch name to create"),
    base: str | None = typer.Option(None, "--base", "-b", help="Base branch"),
) -> None:
    """Create and switch to a new branch."""
    name = _coerce(name)
    base = _coerce(base)
    root = find_workspace_root()
    wf = GitWorkflow(root)
    try:
        wf.ensure_repo()
    except GitWorkflowError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if wf.branch(str(name), base=base):
        get_console().print(f"[green]Created and switched to branch: {name}[/green]")


def git_status_cmd() -> None:
    """Show git status."""
    root = find_workspace_root()
    wf = GitWorkflow(root)
    _run_workflow("status", wf.status)
