"""TUI command for full interactive interface."""

from __future__ import annotations

import typer
from beep.utils.console import get_console



def tui_cmd(
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
    mode: str = typer.Option("assistant", "--mode", help="Chat mode"),
) -> None:
    """Launch full TUI interface."""
    from beep.setup_wizard import ensure_configured

    config = ensure_configured()

    from beep.tui.app import run_tui
    try:
        run_tui(config, model=model, mode=mode)
    except KeyboardInterrupt:
        get_console().print("\n[yellow]TUI closed[/yellow]")
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
