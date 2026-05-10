"""Productivity commands: bookmarks, tasks, search, security, sandbox."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.table import Table

from beep.chat.commands.base import Command
from beep.chat.session_runtime_state import get_session_task_manager


from beep.utils.console import get_console
# --- Bookmarks ---


class BookmarkCommand(Command):
    """Manage file bookmarks."""

    @property
    def name(self) -> str:
        return "bookmark"

    @property
    def description(self) -> str:
        return "Manage bookmarks (add/remove/list/get)"

    @property
    def category(self) -> str:
        return "Productivity"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        from beep.app_service import get_app_service

        mgr = get_app_service().bookmarks

        if not args:
            bookmarks = mgr.list_all()
            if not bookmarks:
                get_console().print("[yellow]No bookmarks[/yellow]")
                return
            table = Table(title="Bookmarks")
            table.add_column("Name", style="cyan")
            table.add_column("Path")
            table.add_column("Uses", justify="right")
            for b in bookmarks:
                table.add_row(b.name, b.path, str(b.access_count))
            get_console().print(table)
            return

        parts = args.split(maxsplit=2)
        action = parts[0].lower()

        if action == "add" and len(parts) >= 3:
            path = Path(parts[2])
            if not path.is_absolute():
                path = ctx["session"]._workspace / path
            result = mgr.add(parts[1], path)
            get_console().print(result)
        elif action == "remove" and len(parts) >= 2:
            get_console().print(mgr.remove(parts[1]))
        elif action == "get" and len(parts) >= 2:
            path = mgr.get(parts[1])
            if path:
                get_console().print(f"[green]{parts[1]} -> {path}[/green]")
            else:
                get_console().print(f"[red]Bookmark not found: {parts[1]}[/red]")
        else:
            get_console().print(
                "[yellow]Usage: /bookmark | /bookmark add <name> <path> | "
                "/bookmark remove <name> | /bookmark get <name>[/yellow]"
            )


# --- Background Tasks ---


class TaskCommand(Command):
    """Manage background tasks."""

    @property
    def name(self) -> str:
        return "task"

    @property
    def description(self) -> str:
        return "Run/list/cancel background tasks"

    @property
    def category(self) -> str:
        return "Productivity"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        mgr = get_session_task_manager(ctx["session"])

        if not args:
            tasks = mgr.list_all()
            if not tasks:
                get_console().print("[yellow]No tasks[/yellow]")
                return
            table = Table(title="Tasks")
            table.add_column("ID", style="cyan")
            table.add_column("Name")
            table.add_column("Command")
            table.add_column("Status")
            for t in tasks:
                table.add_row(t.id, t.name, t.command, t.status.value)
            get_console().print(table)
            return

        parts = args.split(maxsplit=1)
        action = parts[0].lower()

        if action == "run" and len(parts) >= 2:
            sub = parts[1].split(maxsplit=1)
            name = sub[0]
            cmd = sub[1] if len(sub) > 1 else name
            cwd = str(ctx["session"]._workspace)
            task = await mgr.start(name, cmd, cwd=cwd)
            get_console().print(f"[green]Started: {task.name} ({task.id})[/green]")
        elif action == "status" and len(parts) >= 2:
            task = mgr.get(parts[1])
            if task:
                get_console().print(f"[bold]{task.name}[/bold] - {task.status.value}")
                if task.output:
                    get_console().print(f"[dim]{task.output[:500]}[/dim]")
                if task.error:
                    get_console().print(f"[red]{task.error[:500]}[/red]")
            else:
                get_console().print(f"[red]Task not found: {parts[1]}[/red]")
        elif action == "cancel" and len(parts) >= 2:
            ok = await mgr.cancel(parts[1])
            get_console().print("[green]Cancelled[/green]" if ok else "[red]Could not cancel[/red]")
        else:
            get_console().print(
                "[yellow]Usage: /task | /task run <name> <cmd> | "
                "/task status <id> | /task cancel <id>[/yellow]"
            )


# --- Web Search ---


class SearchCommand(Command):
    """Search the web."""

    @property
    def name(self) -> str:
        return "web"

    @property
    def description(self) -> str:
        return "Search the web for current info"

    @property
    def category(self) -> str:
        return "Productivity"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        from beep.websearch.search import search_web

        if not args:
            get_console().print("[yellow]Usage: /web <query>[/yellow]")
            return

        get_console().print(f"[dim]Searching: {args}[/dim]")
        results = await search_web(args)

        table = Table(title=f"Results for '{args}'")
        table.add_column("#", justify="right")
        table.add_column("Title", style="cyan")
        table.add_column("Snippet")
        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.title, r.snippet[:150])
        get_console().print(table)


class FetchCommand(Command):
    """Fetch URL content."""

    @property
    def name(self) -> str:
        return "fetch"

    @property
    def description(self) -> str:
        return "Fetch and display URL content"

    @property
    def category(self) -> str:
        return "Productivity"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        from beep.websearch.search import fetch_url

        if not args:
            get_console().print("[yellow]Usage: /fetch <url>[/yellow]")
            return

        get_console().print(f"[dim]Fetching: {args}[/dim]")
        content = await fetch_url(args)
        get_console().print(content[:1000])


# --- Security Scan ---


class ScanCommand(Command):
    """Security vulnerability scan."""

    @property
    def name(self) -> str:
        return "scan"

    @property
    def description(self) -> str:
        return "Scan code for security issues"

    @property
    def category(self) -> str:
        return "Quality"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        from beep.security.scanner import display_findings, scan_directory, scan_file

        if args:
            path = Path(args)
            if not path.is_absolute():
                path = ctx["session"]._workspace / path
            if path.is_file():
                findings = scan_file(path)
            elif path.is_dir():
                findings = scan_directory(path)
            else:
                get_console().print(f"[red]Not found: {args}[/red]")
                return
        else:
            findings = scan_directory(ctx["session"]._workspace)

        display_findings(findings)


# --- Code Sandbox ---


class RunCodeCommand(Command):
    """Execute code snippets."""

    @property
    def name(self) -> str:
        return "run"

    @property
    def description(self) -> str:
        return "Run Python/JS code snippet"

    @property
    def category(self) -> str:
        return "Productivity"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        from beep.sandbox.executor import execute_javascript, execute_python

        if not args:
            get_console().print("[yellow]Usage: /run python <code> | /run js <code>[/yellow]")
            return

        parts = args.split(maxsplit=1)
        lang = parts[0].lower()
        code = parts[1] if len(parts) > 1 else ""

        if not code:
            get_console().print("[yellow]No code provided[/yellow]")
            return

        cwd = ctx["session"]._workspace

        if lang in ("python", "py"):
            result = await execute_python(code, cwd=cwd)
        elif lang in ("javascript", "js", "node"):
            result = await execute_javascript(code, cwd=cwd)
        else:
            get_console().print(f"[red]Unknown language: {lang}[/red]")
            return

        if result.success:
            get_console().print(f"[green]OK ({result.duration:.2f}s)[/green]")
        else:
            get_console().print(f"[red]Failed (exit {result.exit_code})[/red]")

        if result.stdout:
            get_console().print(result.stdout[:1000])
        if result.stderr:
            get_console().print(f"[red]{result.stderr[:500]}[/red]")


# --- Fuzzy File Picker ---


class PickCommand(Command):
    """Fuzzy file picker."""

    @property
    def name(self) -> str:
        return "pick"

    @property
    def description(self) -> str:
        return "Fuzzy search for files"

    @property
    def category(self) -> str:
        return "Productivity"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        from beep.completion.fuzzy import pick_file

        path = await pick_file(
            workspace_root=ctx["session"]._workspace,
            prompt_text=args or "Search files",
        )
        if path:
            get_console().print(f"[green]Selected: {path}[/green]")
