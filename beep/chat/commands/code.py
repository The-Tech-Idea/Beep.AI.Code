"""Code commands: /cat, /tree, /grep, /edit, /add, /remove."""

from __future__ import annotations

from pathlib import Path
from typing import Any


from beep.chat.commands.base import Command
from beep.workspace.detector import find_workspace_root
from beep.workspace.search import search_workspace
from beep.workspace.view import read_workspace_file, show_workspace_tree



from beep.utils.console import get_console
class CatCommand(Command):
    @property
    def name(self) -> str:
        return "cat"

    @property
    def description(self) -> str:
        return "View file with syntax highlighting"

    @property
    def category(self) -> str:
        return "Code"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /cat <path>[/yellow]")
            return
        try:
            content = read_workspace_file(args, show_numbers=True, highlight=True)
        except (ValueError, RuntimeError) as exc:
            get_console().print(f"[red]{exc}[/red]")
            return
        get_console().print(content)


class TreeCommand(Command):
    @property
    def name(self) -> str:
        return "tree"

    @property
    def description(self) -> str:
        return "Show file tree"

    @property
    def category(self) -> str:
        return "Code"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        root = Path(args) if args else find_workspace_root()
        try:
            show_workspace_tree(root)
        except (ValueError, RuntimeError) as exc:
            get_console().print(f"[red]{exc}[/red]")


class GrepCommand(Command):
    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search files with regex"

    @property
    def category(self) -> str:
        return "Code"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /grep <pattern>[/yellow]")
            return
        try:
            result = search_workspace(Path(find_workspace_root()), pattern=args)
        except ValueError as exc:
            get_console().print(f"[red]{exc}[/red]")
            return

        for match in result.matches:
            get_console().print(
                f"[cyan]{match.relative_path}[/cyan]:[green]{match.line_number}[/green]: {match.line_text}"
            )
        if not result.matches:
            get_console().print("[yellow]No matches[/yellow]")


class EditCommand(Command):
    @property
    def name(self) -> str:
        return "edit"

    @property
    def description(self) -> str:
        return "Edit file (next lines = content)"

    @property
    def category(self) -> str:
        return "Code"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /edit <path>[/yellow]")
            return
        ctx["session"]._edit_target = Path(args)


class AddCommand(Command):
    @property
    def name(self) -> str:
        return "add"

    @property
    def description(self) -> str:
        return "Pin file to context"

    @property
    def category(self) -> str:
        return "Code"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /add <path>[/yellow]")
            return
        result = ctx["chat_context"].pin_file(Path(args))
        get_console().print(result)


class RemoveCommand(Command):
    @property
    def name(self) -> str:
        return "remove"

    @property
    def description(self) -> str:
        return "Unpin file from context"

    @property
    def category(self) -> str:
        return "Code"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /remove <path>[/yellow]")
            return
        result = ctx["chat_context"].unpin_file(Path(args))
        get_console().print(result)
