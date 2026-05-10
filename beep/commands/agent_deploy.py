"""Hosted deployment helpers for portable agent bundles."""

from __future__ import annotations

import argparse
from pathlib import Path

import typer

from beep.api.client import BeepAPIClient
from beep.agent.bundle_store import resolve_bundle_manifest
from beep.cli_support_async import run_async_cmd
from beep.config import load_config
from beep.publishing.server_deploy_support import build_server_deployment_plan
from beep.utils.console import get_console


class _AgentDeployArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - exercised through callers
        raise ValueError(message)


def agent_deploy_cmd(
    bundle_reference: str,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> None:
    config = load_config()
    try:
        manifest, resolved_bundle_path = resolve_bundle_manifest(bundle_reference)
        plan = build_server_deployment_plan(
            manifest,
            server_url=config.server_url,
            bundle_reference=str(resolved_bundle_path),
            overwrite=overwrite,
        )
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    if dry_run:
        get_console().print(
            f"[green]Dry-run deploy plan for {manifest.agent_id} to {plan.server_url}{plan.endpoint_path}[/green]"
        )
        release_tag = str(plan.shared_release_metadata.get("tag_name", "")).strip()
        if release_tag:
            get_console().print(f"[cyan]Release Tag:[/cyan] {release_tag}")
        get_console().print(f"[cyan]Bundle:[/cyan] {plan.bundle_reference}")
        get_console().print(f"[cyan]Expected Execution Target:[/cyan] {plan.expected_execution_target}")
        get_console().print(
            f"[cyan]Declared Runner Kinds:[/cyan] {', '.join(plan.declared_runner_kinds) or 'none'}"
        )
        get_console().print(f"[cyan]Overwrite Existing Agent:[/cyan] {'Yes' if plan.overwrite else 'No'}")
        for warning in plan.warnings:
            get_console().print(f"[yellow]Warning: {warning}[/yellow]")
        return

    if not str(config.api_token or "").strip():
        get_console().print(
            "[red]An API token is required for hosted deployment. Run `beep config-set api_token <token>` first.[/red]"
        )
        raise typer.Exit(1)

    async def _run() -> None:
        client = BeepAPIClient(config)
        try:
            result = await client.import_agent_bundle(bundle=manifest.to_dict(), overwrite=overwrite)
        finally:
            await client.close()

        agent_payload = result.get("agent") if isinstance(result.get("agent"), dict) else {}
        get_console().print(
            f"[green]Deployed bundle {manifest.agent_id} to {plan.server_url}{plan.endpoint_path}[/green]"
        )
        release_tag = str(plan.shared_release_metadata.get("tag_name", "")).strip()
        if release_tag:
            get_console().print(f"[cyan]Release Tag:[/cyan] {release_tag}")
        get_console().print(
            f"[cyan]Created:[/cyan] {'Yes' if bool(result.get('created')) else 'No'}"
        )
        get_console().print(
            f"[cyan]Execution Target:[/cyan] {agent_payload.get('execution_target', plan.expected_execution_target)}"
        )
        get_console().print(
            f"[cyan]Contract Version:[/cyan] {result.get('contract_version', 'unknown')}"
        )
        for warning in plan.warnings:
            get_console().print(f"[yellow]Warning: {warning}[/yellow]")
        result_warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
        for warning in result_warnings:
            get_console().print(f"[yellow]Warning: {warning}[/yellow]")

    run_async_cmd(_run, cancel_message="Agent deployment cancelled")


def run_agent_deploy_from_argv(argv: list[str]) -> None:
    parser = _AgentDeployArgumentParser(prog="beep agent deploy", add_help=False)
    parser.add_argument("bundle_reference")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")

    try:
        parsed = parser.parse_args(argv)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    agent_deploy_cmd(
        parsed.bundle_reference,
        overwrite=bool(parsed.force),
        dry_run=bool(parsed.dry_run),
    )