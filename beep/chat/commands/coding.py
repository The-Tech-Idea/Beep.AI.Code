"""Coding assistant toggle command: /coding."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command
from beep.utils.json_logging import log_event



from beep.utils.console import get_console
class CodingCommand(Command):
    @property
    def name(self) -> str:
        return "coding"

    @property
    def description(self) -> str:
        return "Toggle coding assistant"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx.get("session")
        if not session:
            get_console().print("[red]No active session[/red]")
            return

        if not args:
            status = "on" if session.coding_enabled else "off"
            get_console().print(f"Coding assistant: [cyan]{status}[/cyan]")
            if session.coding_project_id:
                get_console().print(
                    f"[dim]Project: {session.coding_project_id}, "
                    f"Session: {session.coding_session_id}[/dim]"
                )
            return

        if args.lower() in ("on", "enable", "true"):
            session.set_coding_enabled(True)
            log_event(
                "chat.coding.enabled",
                session_id=getattr(session, "_session_id", ""),
            )
            get_console().print("[green]Coding assistant enabled[/green]")
        elif args.lower() in ("off", "disable", "false"):
            session.set_coding_enabled(False)
            session._coding_project_id = None
            session._coding_session_id = None
            log_event(
                "chat.coding.disabled",
                session_id=getattr(session, "_session_id", ""),
            )
            get_console().print("[yellow]Coding assistant disabled[/yellow]")
        else:
            get_console().print("[yellow]Usage: /coding [on|off][/yellow]")
