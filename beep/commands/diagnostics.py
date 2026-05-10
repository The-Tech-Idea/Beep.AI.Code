"""Diagnostics commands."""

from __future__ import annotations

from pathlib import Path

import typer

from beep.commands.diagnostics_runtime_support import (
    collect_agent_runtime_status as _collect_agent_runtime_status_impl,
    collect_diagnostics_state as _collect_diagnostics_state_impl,
    doctor_has_manual_issues as _doctor_has_manual_issues_impl,
    render_diagnostics_state as _render_diagnostics_state_impl,
    supported_auto_repairs as _supported_auto_repairs_impl,
)
from beep.commands.diagnostics_schema_support import (
    build_repair_guidance as _build_repair_guidance_impl,
    inspect_config_schema as _inspect_config_schema_impl,
    inspect_session_history_schema as _inspect_session_history_schema_impl,
    inspect_workspace_session_memory_schema as _inspect_workspace_session_memory_schema_impl,
)
from beep.utils.console import get_console


def _inspect_config_schema(config_file: Path, *, expected_schema: int) -> dict[str, object]:
    return _inspect_config_schema_impl(config_file, expected_schema=expected_schema)


def _inspect_session_history_schema(
    history_dir: Path, *, expected_schema: int
) -> dict[str, object]:
    return _inspect_session_history_schema_impl(history_dir, expected_schema=expected_schema)


def _inspect_workspace_session_memory_schema(
    workspace: Path,
    *,
    expected_schema: int,
) -> dict[str, object]:
    return _inspect_workspace_session_memory_schema_impl(
        workspace,
        expected_schema=expected_schema,
    )


def _collect_agent_runtime_status() -> dict[str, object]:
    return _collect_agent_runtime_status_impl()


def _build_repair_guidance(
    *,
    config: object,
    config_schema: dict[str, object],
    agent_runtime: dict[str, object],
    history_schema: dict[str, object],
    session_memory_schema: dict[str, object],
) -> list[str]:
    return _build_repair_guidance_impl(
        config=config,
        config_schema=config_schema,
        agent_runtime=agent_runtime,
        history_schema=history_schema,
        session_memory_schema=session_memory_schema,
    )


def _collect_diagnostics_state() -> dict[str, object]:
    return _collect_diagnostics_state_impl(
        inspect_config_schema=_inspect_config_schema,
        collect_agent_runtime_status=_collect_agent_runtime_status,
        inspect_session_history_schema=_inspect_session_history_schema,
        inspect_workspace_session_memory_schema=_inspect_workspace_session_memory_schema,
        build_repair_guidance=_build_repair_guidance,
    )


def _render_diagnostics_state(state: dict[str, object]) -> None:
    _render_diagnostics_state_impl(state)


def _supported_auto_repairs(state: dict[str, object]) -> list[tuple[str, Callable[[], None]]]:
    return _supported_auto_repairs_impl(state)


def _doctor_has_manual_issues(state: dict[str, object]) -> bool:
    return _doctor_has_manual_issues_impl(state)


def doctor_cmd(*, fix: bool = False) -> None:
    try:
        state = _collect_diagnostics_state()
        _render_diagnostics_state(state)
        if not fix:
            return

        repairs = _supported_auto_repairs(state)
        if repairs:
            get_console().print("\n[bold]Applying Supported Repairs:[/bold]")
            for label, operation in repairs:
                get_console().print(f"  - {label}")
                operation()
            get_console().print(
                "[green]Supported repairs completed.[/green] Re-run `beep doctor` to verify the updated state."
            )
            return

        if _doctor_has_manual_issues(state):
            get_console().print(
                "[red]No supported automatic repairs are available for the current issues.[/red]"
            )
            raise typer.Exit(1)

        get_console().print("[green]No automatic repairs are needed.[/green]")
    except Exception as exc:
        if isinstance(exc, typer.Exit):
            raise
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def diagnostics_cmd() -> None:
    """Show diagnostics and system info."""
    try:
        state = _collect_diagnostics_state()
        _render_diagnostics_state(state)
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
