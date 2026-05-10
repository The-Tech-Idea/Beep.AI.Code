"""Local channel packaging helpers for portable agent bundles."""

from __future__ import annotations

import argparse
from pathlib import Path

import typer

from beep.agent.bundle_contract import evaluate_bundle_compatibility
from beep.agent.bundle_store import resolve_bundle_manifest
from beep.publishing import (
    SUPPORTED_PACKAGE_CHANNELS,
    build_channel_package_plans,
    write_channel_package_plan,
)
from beep.utils.console import get_console


class _AgentPackageArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - exercised through callers
        raise ValueError(message)


def agent_package_cmd(
    bundle_reference: str,
    *,
    channels: list[str] | None = None,
    output: Path | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
) -> list[Path]:
    try:
        manifest, resolved_bundle_path = resolve_bundle_manifest(bundle_reference)
        compatibility_runner = manifest.runtime.supported_runner_kinds[0]
        report = evaluate_bundle_compatibility(manifest, runner_kind=compatibility_runner)
        package_plans = build_channel_package_plans(manifest, channels=channels)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    if not report.compatible:
        for error in report.errors:
            get_console().print(f"[red]{error}[/red]")
        raise typer.Exit(1)
    for warning in report.warnings:
        get_console().print(f"[yellow]Warning: {warning}[/yellow]")

    output_root = output or (Path.cwd() / f"{manifest.agent_id}-packages")
    if dry_run:
        get_console().print(
            f"[green]Dry-run packaging plan for {manifest.agent_id} from {resolved_bundle_path}[/green]"
        )
        for plan in package_plans:
            target_root = output_root / plan.root_dir_name
            get_console().print(
                f"[cyan]{plan.channel}[/cyan] -> {target_root} "
                f"({len(plan.files)} files, package {plan.package_name}@{plan.package_version})"
            )
            for package_file in plan.files:
                get_console().print(f"  - {package_file.relative_path}")
        return []

    written_paths: list[Path] = []
    for plan in package_plans:
        try:
            written_paths.append(write_channel_package_plan(plan, output_root, overwrite=overwrite))
        except ValueError as exc:
            get_console().print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc

    for written_path in written_paths:
        get_console().print(f"[green]Wrote package artifacts to {written_path}[/green]")
    return written_paths


def run_agent_package_from_argv(argv: list[str]) -> None:
    parser = _AgentPackageArgumentParser(prog="beep agent package", add_help=False)
    parser.add_argument("bundle_reference")
    parser.add_argument(
        "--channel",
        action="append",
        choices=list(SUPPORTED_PACKAGE_CHANNELS),
        default=[],
    )
    parser.add_argument("--output", "-o")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")

    try:
        parsed = parser.parse_args(argv)
    except ValueError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    agent_package_cmd(
        parsed.bundle_reference,
        channels=list(parsed.channel),
        output=Path(parsed.output) if parsed.output else None,
        dry_run=bool(parsed.dry_run),
        overwrite=bool(parsed.force),
    )