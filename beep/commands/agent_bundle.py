"""Portable agent bundle command helpers."""

from __future__ import annotations

import argparse
from pathlib import Path

import typer

from beep.agent.loop import run_agent
from beep.agent.bundle_contract import evaluate_bundle_compatibility
from beep.agent.bundle_store import (
    build_bundle_from_config,
    build_runtime_config_from_bundle,
    default_bundle_output_path,
    install_bundle_manifest,
    load_bundle_manifest,
    resolve_bundle_manifest,
    write_bundle_manifest,
)
from beep.coding.metadata import build_coding_metadata
from beep.config import load_config
from beep.mcp.discovery import resolve_mcp_configuration
from beep.permissions.manager import SandboxMode, coerce_sandbox_mode
from beep.cli_support_async import run_async_cmd
from beep.utils.console import get_console
from beep.workspace.detector import find_workspace_root


class _AgentBundleArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - exercised through callers
        raise ValueError(message)


def agent_export_cmd(
    agent_id: str,
    *,
    output: Path | None = None,
    name: str | None = None,
    description: str = "",
    system_prompt_file: Path | None = None,
    tags: list[str] | None = None,
    created_by: str = "",
    source_repository: str = "",
    source_revision: str = "",
    runner_kinds: list[str] | None = None,
    overwrite: bool = False,
) -> Path:
    config = load_config()
    system_prompt = ""
    if system_prompt_file is not None:
        try:
            system_prompt = system_prompt_file.read_text(encoding="utf-8")
        except OSError as exc:
            get_console().print(f"[red]Failed to read system prompt file: {exc}[/red]")
            raise typer.Exit(1) from exc

    try:
        manifest = build_bundle_from_config(
            config,
            agent_id=agent_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            tags=tags,
            created_by=created_by,
            source_repository=source_repository,
            source_revision=source_revision,
            runner_kinds=runner_kinds,
        )
        destination = output or default_bundle_output_path(agent_id)
        path = write_bundle_manifest(manifest, destination, overwrite=overwrite)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    get_console().print(f"[green]Exported agent bundle to {path}[/green]")
    return path


def agent_import_cmd(
    bundle_file: Path,
    *,
    output: Path | None = None,
    overwrite: bool = False,
    runner_kind: str = "local",
) -> Path:
    try:
        manifest = load_bundle_manifest(bundle_file)
        report = evaluate_bundle_compatibility(manifest, runner_kind=runner_kind)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    if not report.compatible:
        for error in report.errors:
            get_console().print(f"[red]{error}[/red]")
        raise typer.Exit(1)
    for warning in report.warnings:
        get_console().print(f"[yellow]Warning: {warning}[/yellow]")

    try:
        path = install_bundle_manifest(manifest, destination=output, overwrite=overwrite)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    get_console().print(f"[green]Imported agent bundle to {path}[/green]")
    return path


def _select_mcp_servers_for_bundle(
    bundle_server_ids: list[str],
    *,
    available_servers: list[object],
) -> list[object]:
    if not bundle_server_ids:
        return []
    by_name = {
        str(getattr(server, "name", "")).strip(): server
        for server in available_servers
        if str(getattr(server, "name", "")).strip()
    }
    missing = [server_id for server_id in bundle_server_ids if server_id not in by_name]
    if missing:
        raise ValueError(
            "Bundle references MCP servers that are not available locally: " + ", ".join(sorted(missing))
        )
    return [by_name[server_id] for server_id in bundle_server_ids]


def agent_run_bundle_cmd(
    bundle_reference: str,
    goal: str,
    *,
    max_steps: int,
    auto_approve: bool,
    sandbox: SandboxMode,
    model: str | None,
    no_plugins: bool,
    response_json: bool,
    response_schema: Path | None,
    input_file: list[Path] | None,
    input_image: list[Path] | None,
) -> None:
    try:
        manifest, resolved_bundle_path = resolve_bundle_manifest(bundle_reference)
        report = evaluate_bundle_compatibility(manifest, runner_kind="local")
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    if not report.compatible:
        for error in report.errors:
            get_console().print(f"[red]{error}[/red]")
        raise typer.Exit(1)
    for warning in report.warnings:
        get_console().print(f"[yellow]Warning: {warning}[/yellow]")

    base_config = load_config()
    runtime_config = build_runtime_config_from_bundle(
        manifest,
        base_config=base_config,
        model_override=model,
    )
    if not runtime_config.is_agent_configured:
        get_console().print(
            "[red]Local credentials for the bundle provider are not configured. "
            f"Run `beep agent configure {manifest.model.provider_key}` first.[/red]"
        )
        raise typer.Exit(1)

    workspace_root = find_workspace_root()
    resolved_mcp = resolve_mcp_configuration(base_config, workspace_root)
    try:
        selected_mcp_servers = (
            _select_mcp_servers_for_bundle(
                manifest.mcp_server_ids,
                available_servers=resolved_mcp.servers,
            )
            if manifest.tool_policy.allow_mcp_tools
            else []
        )
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    from beep.commands.agent_inputs import (
        build_agent_initial_user_content,
        build_agent_response_format,
    )

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

    effective_sandbox = coerce_sandbox_mode(sandbox)

    async def _run() -> None:
        await run_agent(
            None,
            goal,
            config=runtime_config,
            workspace_root=workspace_root,
            max_steps=max_steps,
            auto_approve=auto_approve,
            sandbox_mode=effective_sandbox,
            plugins_enabled=not no_plugins,
            coding_assistant=build_coding_metadata(
                workspace_root=workspace_root,
                interaction_mode="agent",
                project_id=runtime_config.project_id,
            ),
            mcp_enabled=bool(selected_mcp_servers),
            mcp_servers=selected_mcp_servers,
            response_format=response_format,
            initial_user_content=initial_user_content,
            bundle_manifest=manifest,
        )

    get_console().print(f"[green]Running bundle {manifest.agent_id} from {resolved_bundle_path}[/green]")
    run_async_cmd(_run, cancel_message="Agent stopped")


def run_agent_export_from_argv(argv: list[str]) -> None:
    parser = _AgentBundleArgumentParser(prog="beep agent export", add_help=False)
    parser.add_argument("agent_id")
    parser.add_argument("--output", "-o")
    parser.add_argument("--name")
    parser.add_argument("--description", default="")
    parser.add_argument("--system-prompt-file")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--created-by", default="")
    parser.add_argument("--source-repository", default="")
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--runner", action="append", default=[])
    parser.add_argument("--force", action="store_true")

    try:
        parsed = parser.parse_args(argv)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    agent_export_cmd(
        parsed.agent_id,
        output=Path(parsed.output) if parsed.output else None,
        name=parsed.name,
        description=parsed.description,
        system_prompt_file=Path(parsed.system_prompt_file) if parsed.system_prompt_file else None,
        tags=list(parsed.tag),
        created_by=parsed.created_by,
        source_repository=parsed.source_repository,
        source_revision=parsed.source_revision,
        runner_kinds=list(parsed.runner),
        overwrite=bool(parsed.force),
    )


def run_agent_import_from_argv(argv: list[str]) -> None:
    parser = _AgentBundleArgumentParser(prog="beep agent import", add_help=False)
    parser.add_argument("bundle_file")
    parser.add_argument("--output", "-o")
    parser.add_argument("--runner", default="local")
    parser.add_argument("--force", action="store_true")

    try:
        parsed = parser.parse_args(argv)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    agent_import_cmd(
        Path(parsed.bundle_file),
        output=Path(parsed.output) if parsed.output else None,
        overwrite=bool(parsed.force),
        runner_kind=str(parsed.runner or "local").strip() or "local",
    )


def run_agent_run_from_argv(
    bundle_reference: str,
    goal_tokens: list[str],
    *,
    max_steps: int,
    auto_approve: bool,
    sandbox: SandboxMode,
    model: str | None,
    no_plugins: bool,
    response_json: bool,
    response_schema: Path | None,
    input_file: list[Path] | None,
    input_image: list[Path] | None,
) -> None:
    goal = " ".join(goal_tokens).strip()
    if not goal:
        get_console().print("[yellow]Usage: beep agent run <bundle_file_or_id> <goal>[/yellow]")
        raise typer.Exit(2)
    agent_run_bundle_cmd(
        bundle_reference,
        goal,
        max_steps=max_steps,
        auto_approve=auto_approve,
        sandbox=sandbox,
        model=model,
        no_plugins=no_plugins,
        response_json=response_json,
        response_schema=response_schema,
        input_file=input_file,
        input_image=input_image,
    )
