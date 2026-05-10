"""Base command interface and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Command(ABC):
    """Base class for slash commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name without slash, e.g. 'help'."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description."""

    @property
    def category(self) -> str:
        """Command category for help display."""
        return "General"

    @property
    def aliases(self) -> list[str]:
        """Optional shorter aliases, e.g. ['c'] for 'clear'."""
        return []

    @abstractmethod
    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        """Execute the command.

        Args:
            args: Arguments after the command name
            ctx: Shared context dict with client, session, etc.
        """


class CustomCommand(Command):
    """A project-defined slash command that sends a canned message to the AI."""

    def __init__(self, cmd_name: str, message_template: str) -> None:
        self._cmd_name = cmd_name
        self._message_template = message_template

    @property
    def name(self) -> str:
        return self._cmd_name

    @property
    def description(self) -> str:
        return self._message_template

    @property
    def category(self) -> str:
        return "Project"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        from beep.chat.commands.llm_turns import stream_assistant_turn
        from beep.sessions.history import save_message

        session = ctx.get("session")
        if session is None:
            return
        content = self._message_template
        if args:
            content = f"{content}: {args}"
        session._messages.append({"role": "user", "content": content})
        save_fn = getattr(session, "_save", None)
        if callable(save_fn):
            save_fn("user", content)
        else:
            save_message(session._session_id, {"role": "user", "content": content})
        await stream_assistant_turn(
            session=session,
            client=ctx["client"],
            event="custom_command",
            empty_message="[yellow]No response[/yellow]",
            empty_error="empty_custom_command_response",
        )
