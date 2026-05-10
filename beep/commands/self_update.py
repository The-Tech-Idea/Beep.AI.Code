"""Self-update command for supported Beep.AI.Code install channels."""

from __future__ import annotations

import importlib.metadata as importlib_metadata
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import typer
from rich.markup import escape
from rich.table import Table
from beep.utils.console import get_console

PACKAGE_NAME = "beep-ai-code"


@dataclass(frozen=True)
class UpdateStep:
    command: tuple[str, ...]
    display: str
    cwd: Path | None = None


@dataclass(frozen=True)
class SelfUpdatePlan:
    channel: str
    summary: str
    note: str | None
    can_execute: bool
    steps: tuple[UpdateStep, ...]


def _read_distribution() -> importlib_metadata.Distribution:
    return importlib_metadata.distribution(PACKAGE_NAME)


def _running_in_pipx_environment() -> bool:
    executable = str(Path(sys.executable).resolve()).casefold().replace("\\", "/")
    return "/pipx/venvs/" in executable


def _load_direct_url_metadata(distribution: importlib_metadata.Distribution) -> dict[str, object] | None:
    raw = distribution.read_text("direct_url.json")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _file_url_to_path(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    path = url2pathname(parsed.path)
    if parsed.netloc and parsed.netloc not in {"", "localhost"}:
        path = f"//{parsed.netloc}{path}"
    return Path(path).resolve()


def _build_vcs_requirement(direct_url: dict[str, object]) -> str | None:
    url = direct_url.get("url")
    vcs_info = direct_url.get("vcs_info")
    if not isinstance(url, str) or not isinstance(vcs_info, dict):
        return None
    vcs = vcs_info.get("vcs")
    if not isinstance(vcs, str) or not vcs:
        return None
    revision = vcs_info.get("requested_revision") or vcs_info.get("commit_id")
    requirement = f"{vcs}+{url}"
    if isinstance(revision, str) and revision:
        requirement += f"@{revision}"
    subdirectory = direct_url.get("subdirectory")
    if isinstance(subdirectory, str) and subdirectory:
        requirement += f"#subdirectory={subdirectory}"
    return requirement


def detect_self_update_plan() -> SelfUpdatePlan:
    if _running_in_pipx_environment():
        return SelfUpdatePlan(
            channel="pipx",
            summary="Detected a pipx-managed installation.",
            note="pipx will reuse the original package source when upgrading.",
            can_execute=True,
            steps=(
                UpdateStep(
                    command=("pipx", "upgrade", PACKAGE_NAME),
                    display=f"pipx upgrade {PACKAGE_NAME}",
                ),
            ),
        )

    distribution = _read_distribution()
    direct_url = _load_direct_url_metadata(distribution)

    if direct_url:
        vcs_requirement = _build_vcs_requirement(direct_url)
        if vcs_requirement:
            return SelfUpdatePlan(
                channel="vcs",
                summary="Detected a VCS-backed installation.",
                note="The upgrade will reinstall from the recorded VCS source.",
                can_execute=True,
                steps=(
                    UpdateStep(
                        command=(sys.executable, "-m", "pip", "install", "--upgrade", vcs_requirement),
                        display=f"{sys.executable} -m pip install --upgrade {vcs_requirement}",
                    ),
                ),
            )

        url = direct_url.get("url")
        if isinstance(url, str):
            source_path = _file_url_to_path(url)
            dir_info = direct_url.get("dir_info")
            archive_info = direct_url.get("archive_info")

            if source_path is not None and isinstance(dir_info, dict):
                editable = bool(dir_info.get("editable"))
                steps: list[UpdateStep] = []
                if (source_path / ".git").exists():
                    steps.append(
                        UpdateStep(
                            command=("git", "pull", "--ff-only"),
                            display="git pull --ff-only",
                            cwd=source_path,
                        )
                    )
                if editable:
                    steps.append(
                        UpdateStep(
                            command=(sys.executable, "-m", "pip", "install", "-e", ".[dev]"),
                            display=f"{sys.executable} -m pip install -e \".[dev]\"",
                            cwd=source_path,
                        )
                    )
                    note = (
                        "Editable installs update from the source checkout. "
                        "If the checkout is dirty, sync it manually before rerunning with --yes."
                    )
                else:
                    steps.append(
                        UpdateStep(
                            command=(sys.executable, "-m", "pip", "install", "--upgrade", str(source_path)),
                            display=f"{sys.executable} -m pip install --upgrade {source_path}",
                        )
                    )
                    note = "Local checkout installs upgrade from the source directory recorded in distribution metadata."
                return SelfUpdatePlan(
                    channel="editable" if editable else "local-directory",
                    summary=f"Detected a local {'editable ' if editable else ''}checkout install at {source_path}.",
                    note=note,
                    can_execute=True,
                    steps=tuple(steps),
                )

            if isinstance(archive_info, dict):
                if source_path is not None:
                    return SelfUpdatePlan(
                        channel="local-artifact",
                        summary=f"Detected an install from a local artifact at {source_path}.",
                        note=(
                            "Self-update cannot guess a newer artifact path. Reinstall from a newer wheel or sdist, "
                            "then rerun `beep doctor`."
                        ),
                        can_execute=False,
                        steps=(),
                    )
                return SelfUpdatePlan(
                    channel="remote-artifact",
                    summary="Detected an install from a remote artifact URL.",
                    note="The upgrade will reinstall from the recorded artifact URL.",
                    can_execute=True,
                    steps=(
                        UpdateStep(
                            command=(sys.executable, "-m", "pip", "install", "--upgrade", url),
                            display=f"{sys.executable} -m pip install --upgrade {url}",
                        ),
                    ),
                )

    return SelfUpdatePlan(
        channel="index",
        summary="Detected a standard package-index installation.",
        note="The upgrade will use the package index configured for this Python environment.",
        can_execute=True,
        steps=(
            UpdateStep(
                command=(sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_NAME),
                display=f"{sys.executable} -m pip install --upgrade {PACKAGE_NAME}",
            ),
        ),
    )


def _render_plan(plan: SelfUpdatePlan) -> None:
    table = Table(title="Self Update Plan")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green", overflow="fold")
    table.add_row("Channel", escape(plan.channel))
    table.add_row("Can Execute", "Yes" if plan.can_execute else "No")
    table.add_row("Summary", escape(plan.summary))
    table.add_row("Notes", escape(plan.note or "None"))
    table.add_row(
        "Steps",
        escape("\n".join(step.display for step in plan.steps)) if plan.steps else "None",
    )
    get_console().print(table)


def _run_step(step: UpdateStep) -> None:
    get_console().print(f"[cyan]Running:[/cyan] {step.display}")
    subprocess.run(step.command, cwd=str(step.cwd) if step.cwd else None, check=True)


def self_update_cmd(*, yes: bool = False) -> None:
    try:
        plan = detect_self_update_plan()
    except importlib_metadata.PackageNotFoundError as exc:
        get_console().print(f"[red]Unable to locate installed package metadata: {exc}[/red]")
        raise typer.Exit(1)

    _render_plan(plan)

    if not yes:
        get_console().print("[yellow]Dry run only.[/yellow] Re-run with [bold]--yes[/bold] to execute the detected update steps.")
        return

    if not plan.can_execute:
        get_console().print("[red]Detected install channel cannot be updated automatically.[/red]")
        if plan.note:
            get_console().print(plan.note)
        raise typer.Exit(1)

    try:
        for step in plan.steps:
            _run_step(step)
    except subprocess.CalledProcessError as exc:
        get_console().print(f"[red]Self-update failed while running:[/red] {exc.cmd}")
        raise typer.Exit(exc.returncode or 1)

    get_console().print("[green]Self-update completed.[/green] Run `beep doctor` to verify the updated installation.")