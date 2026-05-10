"""Misc commands: help, quit, retry, summary, clipboard, image, hooks, etc."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.prompt import Confirm

from beep.chat.commands._budget import ensure_budget_available
from beep.chat.commands.base import Command
from beep.chat.commands.environment import (
    HooksCommand,
    InstallCommand,
    MaxTokensCommand,
    SandboxCommand,
)
from beep.chat.commands.extensions import (
    PluginsCommand,
    RulesCommand,
    SkillCommand,
    SkillsCommand,
)
from beep.chat.commands.importing import ImportCommand
from beep.chat.commands.llm_turns import complete_text_turn, stream_assistant_turn


from beep.utils.console import get_console
__all__ = [
    "ClipboardCommand",
    "ExitCommand",
    "HelpCommand",
    "HooksCommand",
    "ImageCommand",
    "ImportCommand",
    "InstallCommand",
    "MaxTokensCommand",
    "PluginsCommand",
    "QuitCommand",
    "RetryCommand",
    "RulesCommand",
    "SandboxCommand",
    "SkillCommand",
    "SkillsCommand",
    "SummaryCommand",
]


class HelpCommand(Command):
    @property
    def name(self) -> str:
        return "help"

    @property
    def description(self) -> str:
        return "Show all commands"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        registry = ctx.get("command_registry", {})
        by_cat: dict[str, list[tuple[str, str]]] = {}
        for cmd in registry.values():
            cat = cmd.category
            by_cat.setdefault(cat, []).append((f"/{cmd.name}", cmd.description))

        for cat in sorted(by_cat):
            get_console().print(f"\n[bold]{cat}[/bold]")
            for name, desc in sorted(by_cat[cat]):
                get_console().print(f"  [cyan]{name}[/cyan] - {desc}")
        plugin_commands = ctx.get("plugin_commands", {})
        if plugin_commands:
            get_console().print("\n[bold]Plugins[/bold]")
            for name, desc in sorted(plugin_commands.items()):
                get_console().print(f"  [cyan]/{name}[/cyan] - {desc}")
        get_console().print()


class QuitCommand(Command):
    @property
    def name(self) -> str:
        return "quit"

    @property
    def description(self) -> str:
        return "Exit"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, _ctx: dict[str, Any]) -> None:
        raise KeyboardInterrupt


class ExitCommand(Command):
    @property
    def name(self) -> str:
        return "exit"

    @property
    def description(self) -> str:
        return "Exit"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, _ctx: dict[str, Any]) -> None:
        raise KeyboardInterrupt


class RetryCommand(Command):
    @property
    def name(self) -> str:
        return "retry"

    @property
    def description(self) -> str:
        return "Retry last request"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        client = ctx["client"]
        if not ensure_budget_available(session, command="retry"):
            return

        if len(session._messages) < 2:
            get_console().print("[yellow]Nothing to retry[/yellow]")
            return

        last_user = None
        for msg in reversed(session._messages):
            if msg["role"] == "user":
                last_user = msg["content"]
                break

        if not last_user:
            get_console().print("[yellow]No user message to retry[/yellow]")
            return

        # Remove only the previous assistant response; keep the last user turn intact
        # when retrying after failures where no assistant message was appended.
        if session._messages and session._messages[-1].get("role") == "assistant":
            session._messages.pop()
        get_console().print("[dim]Retrying...[/dim]")

        await stream_assistant_turn(session=session, client=client, event="retry")


class SummaryCommand(Command):
    @property
    def name(self) -> str:
        return "summary"

    @property
    def description(self) -> str:
        return "Summarize session progress"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        client = ctx["client"]
        if not ensure_budget_available(session, command="summary"):
            return

        if len(session._messages) < 3:
            get_console().print("[yellow]Not enough conversation to summarize[/yellow]")
            return

        messages = [
            {
                "role": "system",
                "content": "Summarize what was accomplished in this conversation. Be concise.",
            },
        ] + session._messages[-10:]

        summary = await complete_text_turn(
            session=session,
            client=client,
            messages=messages,
            event="summary",
            max_tokens=500,
            empty_message="[yellow]Model returned an empty summary[/yellow]",
            empty_error="empty_summary",
        )
        if summary:
            get_console().print(Panel(summary, title="Session Summary", border_style="blue"))


class ClipboardCommand(Command):
    @property
    def name(self) -> str:
        return "clipboard"

    @property
    def description(self) -> str:
        return "Paste clipboard into chat"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        from beep.utils.clipboard import get_clipboard

        content = get_clipboard()
        if not content:
            get_console().print("[yellow]Clipboard is empty[/yellow]")
            return

        if args == "--copy":
            from beep.utils.clipboard import set_clipboard

            session = ctx.get("session")
            last = (
                getattr(session, "_last_output", "")
                if session is not None
                else ctx.get("last_response", "")
            )
            if last:
                set_clipboard(last)
                get_console().print("[green]Copied last response[/green]")
            else:
                get_console().print("[yellow]No recent response to copy[/yellow]")
            return

        get_console().print(f"[dim]Clipboard ({len(content)} chars):[/dim]")
        get_console().print(content[:500] + ("..." if len(content) > 500 else ""))

        if Confirm.ask("Include in chat?"):
            session = ctx["session"]
            if not ensure_budget_available(session, command="clipboard"):
                return
            session._messages.append({"role": "user", "content": content})
            session._save("user", "[clipboard content]")
            await stream_assistant_turn(
                session=session,
                client=ctx["client"],
                event="clipboard",
            )


class ImageCommand(Command):
    @property
    def name(self) -> str:
        return "image"

    @property
    def description(self) -> str:
        return "Include image in prompt"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /image <path>[/yellow]")
            return

        path = Path(args)
        if not path.exists():
            get_console().print(f"[red]Not found: {args}[/red]")
            return

        import base64

        data = base64.b64encode(path.read_bytes()).decode()
        ext = path.suffix.lower().lstrip(".")
        mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "gif", "webp") else "image/png"

        session = ctx["session"]
        if not ensure_budget_available(session, command="image"):
            return
        session._messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
                    {"type": "text", "text": f"Analyze this image: {path.name}"},
                ],
            }
        )
        session._save("user", f"[image: {path.name}]")
        await stream_assistant_turn(session=session, client=ctx["client"], event="image")
