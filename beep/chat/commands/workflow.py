"""Workflow commands: /bash, /diff, /commit, /branch, /pr, /undo, /output."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.panel import Panel
from rich.prompt import Confirm

from beep.chat.commands._budget import ensure_budget_available
from beep.chat.commands.base import Command
from beep.chat.commands.llm_turns import complete_text_turn
from beep.workspace.detector import find_workspace_root
from beep.workspace.git import get_git_diff



from beep.utils.console import get_console
class BashCommand(Command):
    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Run shell command"

    @property
    def category(self) -> str:
        return "Workflow"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /bash <command>[/yellow]")
            return

        root = find_workspace_root()
        session = _ctx.get("session")
        try:
            proc = await asyncio.create_subprocess_shell(
                args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=root,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            combined = out
            if err:
                combined = f"{combined}\n{err}" if combined else err
            if session is not None:
                session._last_output = combined[:10000]

            if out:
                get_console().print(out[:3000])
            if err:
                get_console().print(f"[dim]{err[:1000]}[/dim]")
            if proc.returncode != 0:
                get_console().print(f"[red]Exit code: {proc.returncode}[/red]")
        except Exception as exc:
            get_console().print(f"[red]{e}[/red]")


class DiffCommand(Command):
    @property
    def name(self) -> str:
        return "diff"

    @property
    def description(self) -> str:
        return "Show git diff"

    @property
    def category(self) -> str:
        return "Workflow"

    async def execute(self, _args: str, _ctx: dict[str, Any]) -> None:
        root = find_workspace_root()
        diff = get_git_diff(root)
        if not diff:
            get_console().print("[yellow]No changes[/yellow]")
            return
        get_console().print(Panel(diff, title="Git Diff", border_style="yellow"))


class CommitCommand(Command):
    @property
    def name(self) -> str:
        return "commit"

    @property
    def description(self) -> str:
        return "AI-generate commit message and commit"

    @property
    def category(self) -> str:
        return "Workflow"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        root = find_workspace_root()
        client = ctx["client"]
        session = ctx["session"]
        if not ensure_budget_available(session, command="commit"):
            return

        diff = get_git_diff(root)
        if not diff:
            get_console().print("[yellow]No changes to commit[/yellow]")
            return

        messages = [
            {
                "role": "system",
                "content": (
                    "Generate a concise conventional commit message "
                    "(type: description) based on this diff. "
                    "Output ONLY the commit message, nothing else."
                ),
            },
            {"role": "user", "content": f"Generate commit message for:\n```diff\n{diff}\n```"},
        ]

        msg = await complete_text_turn(
            session=session,
            client=client,
            messages=messages,
            event="commit",
            max_tokens=100,
            empty_message="[yellow]Model returned an empty commit message[/yellow]",
            empty_error="empty_commit_message",
        )
        if not msg:
            return

        get_console().print(f"[green]Proposed commit:[/green] {msg}")
        if Confirm.ask("Commit?"):
            from beep.workspace.git_ext.operations import commit, stage_all

            stage_all(root)
            if commit(root, msg):
                get_console().print("[green]Committed[/green]")


class BranchCommand(Command):
    @property
    def name(self) -> str:
        return "branch"

    @property
    def description(self) -> str:
        return "Create and switch branch"

    @property
    def category(self) -> str:
        return "Workflow"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /branch <name>[/yellow]")
            return
        from beep.workspace.git_ext.operations import (
            create_branch,
            switch_branch,
        )

        root = find_workspace_root()
        if create_branch(root, args):
            switch_branch(root, args)
            get_console().print(f"[green]Created and switched to: {args}[/green]")


class PRCommand(Command):
    @property
    def name(self) -> str:
        return "pr"

    @property
    def description(self) -> str:
        return "Create PR from changes"

    @property
    def category(self) -> str:
        return "Workflow"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        root = find_workspace_root()
        client = ctx["client"]
        session = ctx["session"]
        if not ensure_budget_available(session, command="pr"):
            return

        diff = get_git_diff(root)
        if not diff:
            get_console().print("[yellow]No changes for PR[/yellow]")
            return

        messages = [
            {
                "role": "system",
                "content": (
                    "Generate a PR title and description based on this diff. "
                    "Format: Title on first line, blank line, then description."
                ),
            },
            {"role": "user", "content": f"Generate PR description:\n```diff\n{diff}\n```"},
        ]

        desc = await complete_text_turn(
            session=session,
            client=client,
            messages=messages,
            event="pr",
            empty_message="[yellow]Model returned an empty PR description[/yellow]",
            empty_error="empty_pr_description",
        )
        if not desc:
            return

        get_console().print(Panel(desc, title="PR Description", border_style="blue"))
        get_console().print("[yellow]Use 'gh pr create' to actually create the PR[/yellow]")


class RevertCommand(Command):
    @property
    def name(self) -> str:
        return "revert"

    @property
    def description(self) -> str:
        return "Undo last file change"

    @property
    def category(self) -> str:
        return "Workflow"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        if not session._last_edit:
            get_console().print("[yellow]No edit to undo[/yellow]")
            return

        edit = session._last_edit
        edit["path"].write_text(edit["old"], encoding="utf-8")
        get_console().print(f"[green]Undid changes to {edit['path'].name}[/green]")
        session._last_edit = None


class OutputCommand(Command):
    @property
    def name(self) -> str:
        return "output"

    @property
    def description(self) -> str:
        return "Show last command output"

    @property
    def category(self) -> str:
        return "Workflow"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx.get("session")
        output = (
            getattr(session, "_last_output", "") if session is not None else ctx.get("last_output")
        )
        if not output:
            get_console().print("[yellow]No recent output[/yellow]")
            return
        get_console().print(output[:3000])
