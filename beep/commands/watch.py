"""Watch command for CLI."""

from __future__ import annotations

import asyncio
import time

import typer
from beep.utils.console import get_console


def watch_cmd(
    pattern: str = typer.Option("*.py", "--pattern", "-p", help="File pattern to watch"),
    command: str = typer.Option(..., "--command", "-c", help="Command to run on change"),
    debounce: float = typer.Option(1.0, "--debounce", "-d", help="Debounce seconds"),
    path: str = typer.Option(".", "--path", help="Directory to watch"),
) -> None:
    """Watch files and run a command on changes."""
    from pathlib import Path

    from beep.watcher.service import WatcherService, WatchEvent, execute_watch_event

    root = Path(path).resolve()
    from beep.app_service import get_app_service

    service = get_app_service().watcher(root)
    service.add_rule(pattern, command, debounce)

    def on_event(event: WatchEvent) -> None:
        get_console().print(
            f"\n[dim]{time.strftime('%H:%M:%S')}[/dim] [cyan]{event.file.name}[/cyan] changed"
        )
        get_console().print(f"[dim]Running: {event.rule.command}[/dim]")

        async def _run() -> None:
            result = await execute_watch_event(event)
            if result:
                get_console().print(f"[dim]{result[:200]}[/dim]")

        try:
            asyncio.run(_run())
        except Exception as exc:
            get_console().print(f"[red]Watch callback error: {exc}[/red]")

    get_console().print(f"[green]Watching[/green] {root} for [cyan]{pattern}[/cyan]")
    get_console().print(f"[dim]Command: {command} (debounce: {debounce}s)[/dim]")
    get_console().print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        service.start(on_event)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
        get_console().print("\n[yellow]Watcher stopped[/yellow]")
    except Exception as exc:
        service.stop()
        get_console().print(f"[red]Watcher error: {exc}[/red]")
