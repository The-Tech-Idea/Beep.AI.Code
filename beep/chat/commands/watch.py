"""Watch slash command for REPL."""

from __future__ import annotations

import time
from typing import Any


from beep.chat.commands.base import Command
from beep.chat.session_runtime_state import get_session_watcher



from beep.utils.console import get_console
class WatchCommand(Command):
    @property
    def name(self) -> str:
        return "watch"

    @property
    def description(self) -> str:
        return "Watch files and run commands on change"

    @property
    def category(self) -> str:
        return "Productivity"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        watcher = get_session_watcher(ctx["session"])

        if not args:
            rules = watcher.list_rules()
            if not rules:
                get_console().print("[yellow]No watch rules[/yellow]")
                return
            for i, rule in rules:
                status = "[green]on[/green]" if rule.enabled else "[red]off[/red]"
                get_console().print(f"  {i}. [{rule.pattern}] {rule.command} {status}")
            if watcher.is_running:
                get_console().print("[green]Watcher running[/green]")
            return

        parts = args.split(maxsplit=2)
        action = parts[0].lower()

        if action == "add" and len(parts) >= 3:
            result = watcher.add_rule(parts[1], parts[2])
            get_console().print(f"[green]Rule added: {result}[/green]")
        elif action == "remove" and len(parts) >= 2:
            ok = watcher.remove_rule(int(parts[1]))
            get_console().print("[green]Rule removed[/green]" if ok else "[red]Invalid index[/red]")
        elif action == "start":
            if watcher.is_running:
                get_console().print("[yellow]Already running[/yellow]")
                return

            def on_event(event) -> None:
                get_console().print(
                    f"\n[dim]{time.strftime('%H:%M:%S')}[/dim] "
                    f"[cyan]{event.file.name}[/cyan] -> {event.rule.command}"
                )

            watcher.start(on_event)
            get_console().print("[green]Watcher started[/green]")
        elif action == "stop":
            watcher.stop()
            get_console().print("[yellow]Watcher stopped[/yellow]")
        else:
            get_console().print(
                "[yellow]Usage: /watch | /watch add <pattern> <cmd> | "
                "/watch remove <n> | /watch start | /watch stop[/yellow]"
            )
