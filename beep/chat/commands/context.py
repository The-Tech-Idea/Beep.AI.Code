"""Context command: /context — automatic workspace context status and toggle."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command
from beep.context.auto_context import DEFAULT_AUTO_CONTEXT_BUDGET_CHARS



from beep.utils.console import get_console
class ContextCommand(Command):
    """Show or toggle automatic workspace context injection."""

    @property
    def name(self) -> str:
        return "context"

    @property
    def description(self) -> str:
        return "Auto workspace context"

    @property
    def category(self) -> str:
        return "System"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        arg = args.strip().lower()

        if arg in ("off", "disable", "0"):
            session.set_auto_context_enabled(False)
            get_console().print("[yellow]Automatic workspace context disabled.[/yellow]")
            return

        if arg in ("on", "enable", "1"):
            session.set_auto_context_enabled(True)
            get_console().print("[green]Automatic workspace context enabled.[/yellow]")
            return

        if arg == "budget":
            get_console().print(
                f"[dim]Auto-context budget: {DEFAULT_AUTO_CONTEXT_BUDGET_CHARS} chars "
                f"(~{DEFAULT_AUTO_CONTEXT_BUDGET_CHARS // 3} tokens)[/dim]"
            )
            return

        # Default: show status
        enabled = session.auto_context_enabled
        has_adapter = session._semantic_search_adapter is not None
        adapter_status = "[green]available[/green]" if has_adapter else "[dim]unavailable[/dim]"

        get_console().print(
            f"Automatic workspace context: {'[green]ON[/green]' if enabled else '[yellow]OFF[/yellow]'}"
        )
        get_console().print(f"Semantic search (Semble): {adapter_status}")
        get_console().print(
            f"[dim]Use /context on|off to toggle. Sources: git-modified, keyword match, semantic retrieval.[/dim]"
        )
