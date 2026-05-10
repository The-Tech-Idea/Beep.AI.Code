"""Admin and status helpers for autonomous agent CLI commands."""

from __future__ import annotations

from collections.abc import Callable

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from beep.agent.environment import AgentEnvironmentManager
from beep.config import BeepConfig
from beep.agent.provider_plugins import list_available_agent_provider_guidance
from beep.commands.agent_status_support import (
    get_workspace_intelligence_status,
    render_agent_env_status,
    render_provider_capabilities,
    render_provider_guidance,
    render_provider_status,
    render_workspace_intelligence_capabilities,
    render_workspace_intelligence_reports,
)
from beep.utils.console import get_console


def _run_with_progress(
    operation: Callable[[Callable[[str, int, str], None]], dict[str, object]],
) -> dict[str, object]:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        console=get_console(),
    ) as progress:
        task = progress.add_task("Preparing agent environment", total=100)

        def callback(_stage: str, percent: int, message: str) -> None:
            progress.update(task, description=message, completed=max(0, min(percent, 100)))

        return operation(callback)


def agent_providers_impl(config: BeepConfig, *, plugin_registry: object | None = None) -> None:
    providers = list_available_agent_provider_guidance(config, plugin_registry=plugin_registry)

    table = Table(title="Agent Providers")
    table.add_column("Key", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Source")
    table.add_column("Configured")
    table.add_column("Local")
    table.add_column("Requires")
    table.add_column("Default Base URL", overflow="fold")
    table.add_column("Selected")

    for provider in providers:
        requirements: list[str] = []
        if provider.requires_api_key:
            requirements.append("api_key")
        if provider.requires_model:
            requirements.append("model")
        requirement_text = ", ".join(requirements) if requirements else "None"
        table.add_row(
            provider.key,
            provider.display_name,
            provider.source,
            "Yes" if provider.configured else "No",
            "Yes" if provider.local_runtime else "No",
            requirement_text,
            provider.default_base_url or "None",
            "Yes" if provider.selected else "No",
        )
    get_console().print(table)
    get_console().print("Provider details:")
    for provider in providers:
        get_console().print(
            f" - {provider.key}: {provider.display_name} | source={provider.source} | default_base_url={provider.default_base_url or 'None'}"
        )
    get_console().print("Provider keys: " + ", ".join(provider.key for provider in providers))
    get_console().print(
        "Provider names: "
        + ", ".join(f"{provider.key} = {provider.display_name}" for provider in providers)
    )
    get_console().print(
        "Default base URLs: "
        + ", ".join(
            f"{provider.key} = {provider.default_base_url or 'None'}" for provider in providers
        )
    )


def agent_setup_impl(manager: AgentEnvironmentManager) -> None:
    try:
        status = _run_with_progress(lambda callback: manager.install_required_packages(callback))
    except Exception as exc:
        get_console().print(f"[red]Agent environment setup failed: {exc}[/red]")
        raise typer.Exit(1)
    get_console().print("[green]Agent environment ready.[/green]")
    render_agent_env_status(status)


def agent_status_impl(
    config: BeepConfig,
    manager: AgentEnvironmentManager,
    *,
    plugin_registry: object | None = None,
    workspace_runtime_loader: Callable[[], object],
) -> None:
    status = manager.status()
    render_agent_env_status(status)
    render_provider_status(config, plugin_registry=plugin_registry)
    render_provider_guidance(config, plugin_registry=plugin_registry)
    render_provider_capabilities(config, plugin_registry=plugin_registry)
    workspace_intelligence_reports, capabilities = get_workspace_intelligence_status(
        manager,
        status,
        workspace_runtime_loader=workspace_runtime_loader,
    )
    render_workspace_intelligence_reports(workspace_intelligence_reports)
    render_workspace_intelligence_capabilities(capabilities)


def agent_reinstall_impl(manager: AgentEnvironmentManager, package: str) -> None:
    normalized = package.strip().lower()
    runtime_aliases = {"runtime", "environment", "env", "all"}
    try:
        if normalized in runtime_aliases:
            status = _run_with_progress(lambda callback: manager.reinstall_environment(callback))
        else:
            status = _run_with_progress(
                lambda callback: manager.reinstall_package(package, progress_callback=callback)
            )
    except Exception as exc:
        get_console().print(f"[red]Package reinstall failed: {exc}[/red]")
        raise typer.Exit(1)
    if normalized in runtime_aliases:
        get_console().print("[green]Reinstalled managed agent runtime.[/green]")
    else:
        get_console().print(f"[green]Reinstalled {package}.[/green]")
    render_agent_env_status(status)


def agent_uninstall_impl(manager: AgentEnvironmentManager, *, yes: bool) -> None:
    if not yes and not typer.confirm("Remove the managed agent environment?"):
        get_console().print("[yellow]Uninstall cancelled.[/yellow]")
        raise typer.Exit(0)
    try:
        manager.uninstall_environment()
    except Exception as exc:
        get_console().print(f"[red]Agent environment uninstall failed: {exc}[/red]")
        raise typer.Exit(1)
    get_console().print("[green]Agent environment removed.[/green]")
