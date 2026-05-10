"""Test runner commands."""

from __future__ import annotations

import typer

from beep.testrunner.runner import (
    TestFramework,
    detect_framework,
    display_test_result,
    run_tests,
)
from beep.utils.console import get_console
from beep.cli_support_async import run_async_cmd


def test_cmd(
    file: str | None = typer.Option(None, "--file", "-f", help="Test specific file"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch mode"),
    framework: str | None = typer.Option(None, "--framework", help="Force framework"),
    timeout: int = typer.Option(120, "--timeout", "-t", help="Timeout in seconds"),
) -> None:
    """Run tests."""
    from beep.workspace.detector import find_workspace_root

    workspace_root = find_workspace_root()
    fw = None
    if framework:
        try:
            fw = TestFramework(framework)
        except ValueError:
            get_console().print(f"[red]Unknown framework: {framework}[/red]")
            raise typer.Exit(1)
    else:
        detected = detect_framework(workspace_root)
        get_console().print(f"[dim]Detected: {detected.value}[/dim]")

    async def _run() -> None:
        result = await run_tests(workspace_root, fw, file, watch, timeout)
        display_test_result(result)

    run_async_cmd(_run, cancel_message="Test run cancelled")
