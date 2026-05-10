"""Agent command for autonomous code tasks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import typer
from typer.models import OptionInfo

from beep.agent.environment import AgentEnvironmentManager
from beep.agent.environment_catalog import AGENT_PACKAGES
from beep.agent.loop import resume_agent, run_agent
from beep.api.client import BeepAPIClient
from beep.commands.agent_inputs import (
    build_agent_initial_user_content,
    build_agent_response_format,
)
from beep.commands.agent_admin import (
    agent_providers_impl,
    agent_reinstall_impl,
    agent_setup_impl,
    agent_status_impl,
    agent_uninstall_impl,
)
from beep.coding.metadata import build_coding_metadata
from beep.config import load_config
from beep.mcp.discovery import resolve_mcp_configuration
from beep.permissions.manager import SandboxMode, coerce_sandbox_mode
from beep.plugins.runtime import load_runtime_plugins
from beep.runtime.workspace import get_workspace_runtime
from beep.setup_wizard import ensure_agent_configured
from beep.workspace.detector import find_workspace_root
from beep.utils.console import get_console
from beep.cli_support_async import run_async_cmd


def _resolve_typer_option_default(value: Any) -> Any:
    """Resolve Typer option metadata to its default for direct Python calls."""
    if isinstance(value, OptionInfo):
        return value.default
    return value


def _load_plugin_registry_for_agent_status(workspace_root: object) -> object | None:
    try:
        return load_runtime_plugins(workspace_root).registry
    except Exception as exc:
        get_console().print(
            f"[yellow]Plugin runtime unavailable for agent status surfaces: {exc}[/yellow]"
        )
        return None


def agent_providers_cmd() -> None:
    """List available autonomous-agent providers and their configuration guidance."""
    config = load_config()
    provider_registry = _load_plugin_registry_for_agent_status(find_workspace_root())
    agent_providers_impl(
        config,
        plugin_registry=provider_registry,
    )


def agent_setup_cmd() -> None:
    """Create or update the managed LangGraph runtime environment."""
    agent_setup_impl(AgentEnvironmentManager())


def agent_status_cmd() -> None:
    """Show managed LangGraph runtime environment status."""
    config = load_config()
    workspace_root = find_workspace_root()
    provider_registry = _load_plugin_registry_for_agent_status(workspace_root)
    agent_status_impl(
        config,
        AgentEnvironmentManager(),
        plugin_registry=provider_registry,
        workspace_runtime_loader=lambda: get_workspace_runtime(workspace_root),
    )


def agent_reinstall_cmd(
    package: str = typer.Argument(
        ..., help=f"Package key or runtime ({', '.join(sorted(AGENT_PACKAGES))}, runtime)"
    ),
) -> None:
    """Reinstall one managed runtime package or rebuild the whole runtime."""
    agent_reinstall_impl(AgentEnvironmentManager(), package)


def agent_uninstall_cmd(
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Remove the managed environment without prompting"
    ),
) -> None:
    """Remove the managed LangGraph runtime environment."""
    agent_uninstall_impl(AgentEnvironmentManager(), yes=yes)


def agent_cmd(
    goal: str = typer.Argument(..., help="Goal for the agent"),
    max_steps: int = typer.Option(20, "--max-steps", "-n", help="Maximum steps"),
    step_timeout: float = typer.Option(
        120.0, "--timeout", "-t", help="Seconds to wait for each API call before aborting"
    ),
    auto_approve: bool = typer.Option(False, "--yes", "-y", help="Auto-approve all actions"),
    sandbox: SandboxMode = typer.Option(
        SandboxMode.WORKSPACE_WRITE,
        "--sandbox",
        help="Sandbox mode: read-only, workspace-write, or full-trust.",
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
    no_plugins: bool = typer.Option(False, "--no-plugins", help="Disable plugin loading"),
    response_json: bool = typer.Option(
        False,
        "--response-json",
        help="Request JSON object output from compatible providers.",
    ),
    response_schema: Path | None = typer.Option(
        None,
        "--response-schema",
        help="Path to a JSON schema or full response_format JSON file.",
    ),
    input_file: list[Path] | None = typer.Option(
        None,
        "--input-file",
        help="Attach a text file to the initial user message. Repeat to attach multiple files.",
    ),
    input_image: list[Path] | None = typer.Option(
        None,
        "--input-image",
        help="Attach an image to the initial user message. Repeat to attach multiple images.",
    ),
) -> None:
    """Run autonomous agent to achieve a goal.

    The agent can read files, edit code, search the codebase, and run commands.
    Use --yes to auto-approve destructive operations.
    """
    max_steps = int(_resolve_typer_option_default(max_steps))
    step_timeout = float(_resolve_typer_option_default(step_timeout))
    auto_approve = bool(_resolve_typer_option_default(auto_approve))
    sandbox = _resolve_typer_option_default(sandbox)
    model = _resolve_typer_option_default(model)
    no_plugins = bool(_resolve_typer_option_default(no_plugins))
    response_json = bool(_resolve_typer_option_default(response_json))
    response_schema = _resolve_typer_option_default(response_schema)
    input_file = _resolve_typer_option_default(input_file)
    input_image = _resolve_typer_option_default(input_image)
    workspace_root = find_workspace_root()
    try:
        response_format = build_agent_response_format(
            response_json=response_json,
            response_schema=response_schema,
        )
        initial_user_content = build_agent_initial_user_content(
            input_files=input_file,
            input_images=input_image,
        )
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    effective_sandbox = coerce_sandbox_mode(
        sandbox if isinstance(sandbox, SandboxMode) else SandboxMode.WORKSPACE_WRITE
    )

    _run_agent_operation(
        model=model,
        operation=lambda client, config: run_agent(
            client,
            goal,
            config=config,
            max_steps=max_steps,
            step_timeout=step_timeout,
            auto_approve=auto_approve,
            sandbox_mode=effective_sandbox,
            plugins_enabled=not no_plugins,
            coding_assistant=build_coding_metadata(
                workspace_root=workspace_root,
                interaction_mode="agent",
                project_id=config.project_id,
            ),
            mcp_enabled=resolve_mcp_configuration(config, workspace_root).enabled,
            mcp_servers=resolve_mcp_configuration(config, workspace_root).servers,
            response_format=response_format,
            initial_user_content=initial_user_content,
        ),
    )


def agent_resume_cmd(
    session_id: str = typer.Argument(..., help="Checkpoint thread ID to resume"),
    max_steps: int = typer.Option(20, "--max-steps", "-n", help="Maximum steps"),
    step_timeout: float = typer.Option(
        120.0, "--timeout", "-t", help="Seconds to wait for each API call before aborting"
    ),
    auto_approve: bool = typer.Option(False, "--yes", "-y", help="Auto-approve all actions"),
    sandbox: SandboxMode = typer.Option(
        SandboxMode.WORKSPACE_WRITE,
        "--sandbox",
        help="Sandbox mode: read-only, workspace-write, or full-trust.",
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
    no_plugins: bool = typer.Option(False, "--no-plugins", help="Disable plugin loading"),
    response_json: bool = typer.Option(
        False,
        "--response-json",
        help="Request JSON object output from compatible providers while resuming.",
    ),
    response_schema: Path | None = typer.Option(
        None,
        "--response-schema",
        help="Path to a JSON schema or full response_format JSON file.",
    ),
    input_file: list[Path] | None = typer.Option(
        None,
        "--input-file",
        help="Initial input files are only supported on new runs, not resume.",
    ),
    input_image: list[Path] | None = typer.Option(
        None,
        "--input-image",
        help="Initial input images are only supported on new runs, not resume.",
    ),
) -> None:
    """Resume an autonomous agent thread from the latest SQLite checkpoint."""
    max_steps = int(_resolve_typer_option_default(max_steps))
    step_timeout = float(_resolve_typer_option_default(step_timeout))
    auto_approve = bool(_resolve_typer_option_default(auto_approve))
    sandbox = _resolve_typer_option_default(sandbox)
    model = _resolve_typer_option_default(model)
    no_plugins = bool(_resolve_typer_option_default(no_plugins))
    response_json = bool(_resolve_typer_option_default(response_json))
    response_schema = _resolve_typer_option_default(response_schema)
    input_file = _resolve_typer_option_default(input_file)
    input_image = _resolve_typer_option_default(input_image)
    if input_file or input_image:
        get_console().print(
            "[red]--input-file and --input-image are only supported on new `beep agent <goal>` runs.[/red]"
        )
        raise typer.Exit(2)
    workspace_root = find_workspace_root()
    try:
        response_format = build_agent_response_format(
            response_json=response_json,
            response_schema=response_schema,
        )
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    effective_sandbox = coerce_sandbox_mode(
        sandbox if isinstance(sandbox, SandboxMode) else SandboxMode.WORKSPACE_WRITE
    )

    _run_agent_operation(
        model=model,
        operation=lambda client, config: resume_agent(
            client,
            session_id,
            config=config,
            max_steps=max_steps,
            step_timeout=step_timeout,
            auto_approve=auto_approve,
            sandbox_mode=effective_sandbox,
            plugins_enabled=not no_plugins,
            coding_assistant=build_coding_metadata(
                workspace_root=workspace_root,
                interaction_mode="agent",
                project_id=config.project_id,
            ),
            mcp_enabled=resolve_mcp_configuration(config, workspace_root).enabled,
            mcp_servers=resolve_mcp_configuration(config, workspace_root).servers,
            response_format=response_format,
        ),
    )


def _run_agent_operation(
    *,
    model: str | None,
    operation: Callable[[BeepAPIClient | None, object], Awaitable[object]],
) -> None:
    config = ensure_agent_configured()

    if model:
        config.agent_model = model

    async def _run() -> None:
        await operation(None, config)

    run_async_cmd(_run, cancel_message="Agent stopped")
