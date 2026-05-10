"""Conversation import slash command."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command
from beep.utils.json_logging import log_event



from beep.utils.console import get_console
class ImportCommand(Command):
    @property
    def name(self) -> str:
        return "import"

    @property
    def description(self) -> str:
        return "Import another conversation"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /import <session_id>[/yellow]")
            return

        session = ctx["session"]
        if args == getattr(session, "_session_id", ""):
            get_console().print("[yellow]Cannot import current session into itself[/yellow]")
            return

        from beep.sessions.history import load_session, replace_session

        messages = load_session(args)
        if not messages:
            get_console().print(f"[red]Session not found: {args}[/red]")
            return

        imported_count = 0
        for msg in messages:
            if msg.get("role") != "system":
                session._messages.append(msg)
                imported_count += 1

        replace_session(session._session_id, session._messages)
        session._request_count = sum(1 for msg in session._messages if msg.get("role") == "user")
        # Imported transcript token usage is unknown; reset counters/output cache.
        session._token_count = 0
        session._last_output = ""
        log_event(
            "chat.import.success",
            session_id=getattr(session, "_session_id", ""),
            source_session_id=args,
            imported_messages=imported_count,
        )

        get_console().print(f"[green]Imported {imported_count} messages from {args}[/green]")
