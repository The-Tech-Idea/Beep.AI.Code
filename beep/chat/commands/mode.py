"""Plan/Build mode slash commands for the chat REPL."""

from __future__ import annotations

from typing import Any

from beep.chat.commands.base import Command
from beep.chat.mode_state import (
    MODE_TO_SANDBOX,
    AgentMode,
    build_mode_banner,
)
from beep.utils.console import get_console


def _set_mode(session: Any, mode: AgentMode) -> None:
    session._agent_mode = mode
    session._sandbox_mode = MODE_TO_SANDBOX[mode]
    session._sandbox = mode == AgentMode.PLAN
    banner = build_mode_banner(mode)
    get_console().print(banner)


class PlanCommand(Command):
    @property
    def name(self) -> str:
        return "plan"

    @property
    def description(self) -> str:
        return "Switch to read-only analysis mode (Plan)"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        _set_mode(session, AgentMode.PLAN)


class BuildCommand(Command):
    @property
    def name(self) -> str:
        return "build"

    @property
    def description(self) -> str:
        return "Switch to workspace-write edit mode (Build)"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        _set_mode(session, AgentMode.BUILD)
