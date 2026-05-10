"""Shared rendering and state helpers for system surfaces."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.table import Table

from beep.utils.console import get_console

if TYPE_CHECKING:
    from rich.console import Console


def mask_secret(secret: str | None, *, empty_label: str = "Not set") -> str:
    """Mask sensitive tokens while preserving a short suffix for debugging."""
    return f"***{secret[-4:]}" if secret else empty_label


def render_key_value_table(
    *,
    title: str,
    key_header: str,
    value_header: str,
    rows: Sequence[tuple[str, str]],
    console: Console,
) -> None:
    """Render a simple two-column table."""
    table = Table(title=title)
    table.add_column(key_header, style="cyan")
    table.add_column(value_header, style="green")
    for key, value in rows:
        table.add_row(key, value)
    console.print(table)


def render_health_status(
    *,
    health: Any,
    console: Console,
    title: str,
    prefix_rows: Sequence[tuple[str, str]] = (),
    show_model_tiers: bool = True,
) -> None:
    """Render scalar server-health fields and optional model-tier detail."""
    rows = list(prefix_rows)
    if isinstance(health, dict):
        for key, value in health.items():
            if key == "coding_model_tiers":
                continue
            if isinstance(value, (str, int, float, bool)):
                rows.append((str(key), str(value)))
    render_key_value_table(
        title=title,
        key_header="Property",
        value_header="Value",
        rows=rows,
        console=get_console(),
    )
    if not show_model_tiers or not isinstance(health, dict):
        return
    tiers = health.get("coding_model_tiers")
    if isinstance(tiers, dict) and tiers:
        render_key_value_table(
            title="Model Tiers",
            key_header="Tier",
            value_header="Model",
            rows=[(str(tier), str(model)) for tier, model in tiers.items()],
            console=get_console(),
        )


def build_chat_config_rows(*, config: Any, config_file: Path | str) -> list[tuple[str, str]]:
    """Build the compact config summary used by chat system commands."""
    return [
        ("Server", str(config.server_url)),
        ("Token", mask_secret(getattr(config, "api_token", None))),
        ("Model", str(config.default_model or "(default)")),
        ("File", str(config_file)),
    ]


def build_cli_config_rows(*, config: Any, config_file: Path | str) -> list[tuple[str, str]]:
    """Build the full config summary used by the CLI config command."""
    return [
        ("Server URL", str(config.server_url)),
        ("API Token", mask_secret(getattr(config, "api_token", None))),
        ("Default Model", str(config.default_model or "(server default)")),
        ("Agent Backend", str(config.agent_backend)),
        ("Agent Base URL", str(config.agent_base_url or "(uses server_url)")),
        (
            "Agent API Key",
            mask_secret(getattr(config, "agent_api_key", None), empty_label="(uses api_token)"),
        ),
        ("Agent Model", str(config.agent_model or "(uses default_model)")),
        (
            "Agent Reasoning Effort",
            str(getattr(config, "agent_reasoning_effort", None) or "(provider default)"),
        ),
        (
            "Agent Parallel Tool Calls",
            str(getattr(config, "agent_parallel_tool_calls", None))
            if getattr(config, "agent_parallel_tool_calls", None) is not None
            else "(provider default)",
        ),
        (
            "Agent Thinking Budget",
            str(getattr(config, "agent_thinking_budget_tokens", None) or "(disabled)"),
        ),
        ("Max Tokens", str(config.max_tokens)),
        ("Temperature", str(config.temperature)),
        ("Config File", str(config_file)),
    ]


def collect_chat_diagnostics_state(
    *,
    session: Any,
    workspace_root: Path | str,
    version: str,
    git_repo_lookup: Callable[[Path], bool],
) -> dict[str, object]:
    """Collect the lightweight diagnostics snapshot shown in chat."""
    workspace = Path(workspace_root)
    return {
        "version": version,
        "workspace": workspace,
        "is_git_repo": git_repo_lookup(workspace),
        "session_id": str(session._session_id),
        "message_count": len(session._messages),
        "request_count": int(session._request_count),
        "token_count": int(session._token_count),
    }


def render_chat_diagnostics_state(*, state: dict[str, object], console: Console) -> None:
    """Render the lightweight diagnostics snapshot shown in chat."""
    console.print(f"[bold]Beep.AI.Code v{state['version']}[/bold]")
    console.print(f"Workspace: {state['workspace']}")
    console.print(f"Git: {'Yes' if state['is_git_repo'] else 'No'}")
    console.print(f"Session: {state['session_id']}")
    console.print(f"Messages: {state['message_count']}")
    console.print(f"Requests: {state['request_count']}")
    console.print(f"Est. tokens: {state['token_count']:,}")
