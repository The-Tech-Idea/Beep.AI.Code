"""CLI support utilities for async command execution."""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Callable, Coroutine


from beep.utils.console import print_error, get_console


def run_async_cmd(
    coro_fn: Callable[[], Coroutine[Any, Any, None]],
    *,
    cancel_message: str = "Operation cancelled",
    require_config: bool = False,
) -> None:
    """Run an async CLI command with standard error handling.

    Usage:
        def my_cmd():
            async def _run():
                ...
            run_async_cmd(_run)

    Parameters:
        coro_fn: Async function to execute (called with no arguments).
        cancel_message: Message shown on KeyboardInterrupt.
        require_config: Unused legacy parameter for backward compatibility.
    """
    try:
        asyncio.run(coro_fn())
    except KeyboardInterrupt:
        get_console().print(f"\n[yellow]{cancel_message}[/yellow]")
    except Exception as exc:
        print_error(str(exc))


def run_async_cmd_with_value(
    coro_fn: Callable[..., Coroutine[Any, Any, None]],
    *args: Any,
    cancel_message: str = "Operation cancelled",
    **kwargs: Any,
) -> None:
    """Run an async CLI command that accepts arguments.

    Usage:
        def my_cmd(value):
            async def _run(v):
                ...
            run_async_cmd_with_value(_run, value)
    """
    try:
        asyncio.run(coro_fn(*args, **kwargs))
    except KeyboardInterrupt:
        get_console().print(f"\n[yellow]{cancel_message}[/yellow]")
    except Exception as exc:
        print_error(str(exc))
