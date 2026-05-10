"""Shared console singleton for CLI output."""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console

_console: Console | None = None


def get_console() -> Console:
    """Return a shared Rich Console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def print_error(message: str) -> None:
    """Print an error message in red."""
    get_console().print(f"[red]Error: {message}[/red]")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    get_console().print(f"[yellow]{message}[/yellow]")


def print_success(message: str) -> None:
    """Print a success message in green."""
    get_console().print(f"[green]{message}[/green]")


def print_info(message: str) -> None:
    """Print an informational message."""
    get_console().print(message)


def print_status(message: str, **kwargs: Any) -> Any:
    """Run an operation with a spinner status."""
    return get_console().status(message, **kwargs)
