"""Skills command group — install, remove, update, and list catalog skills."""

from __future__ import annotations

import typer
from rich.table import Table

from beep.integrations.catalog import CURATED_ENTRIES
from beep.integrations.catalog import find as catalog_find
from beep.integrations.installer import install, is_installed, list_installed, remove, update_entry
from beep.integrations.models import EntryKind
from beep.utils.console import get_console


def _render_skills_list() -> None:
    installed = list_installed()
    skill_records = [r for r in installed if r.kind == EntryKind.skill]
    if not skill_records:
        get_console().print(
            "[dim]No skills installed. Use 'beep skills add <id>' to install one.[/dim]"
        )
        return

    table = Table(title="Installed Skills")
    table.add_column("ID", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Source", style="dim")
    table.add_column("Installed At", style="yellow")
    for rec in skill_records:
        installed_at = rec.installed_at.strftime("%Y-%m-%d %H:%M") if rec.installed_at else ""
        table.add_row(rec.id, rec.version or "-", rec.source_url or "-", installed_at)
    get_console().print(table)


def skills_list_cmd() -> None:
    """List installed skills."""
    try:
        _render_skills_list()
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def skills_add_cmd(
    skill_id: str = typer.Argument(..., help="Skill ID to install"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm installation of external skills"),
    allow_network: bool = typer.Option(
        False, "--allow-network", help="Allow network access for skill installation"
    ),
) -> None:
    """Install a skill from the catalog."""
    try:
        entry = catalog_find(skill_id)
        if entry is None:
            get_console().print(f"[red]Skill '{skill_id}' not found in catalog.[/red]")
            available = [e.id for e in CURATED_ENTRIES if e.kind == EntryKind.skill]
            get_console().print(f"[dim]Available skills: {', '.join(available)}[/dim]")
            raise typer.Exit(1)

        if entry.kind != EntryKind.skill:
            get_console().print(f"[red]'{skill_id}' is a {entry.kind.value}, not a skill.[/red]")
            raise typer.Exit(1)

        get_console().print(f"[bold]Installing {entry.name}...[/bold]")
        record = install(
            entry,
            allow_external=yes,
            network_enabled=allow_network,
        )
        get_console().print(f"[green]Installed {record.id} v{record.version or 'latest'}[/green]")
    except PermissionError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def skills_remove_cmd(
    skill_id: str = typer.Argument(..., help="Skill ID to remove"),
) -> None:
    """Remove an installed skill."""
    try:
        if not is_installed(skill_id):
            get_console().print(f"[yellow]Skill '{skill_id}' is not installed.[/yellow]")
            return
        remove(skill_id)
        get_console().print(f"[green]Removed {skill_id}.[/green]")
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def skills_update_cmd(
    skill_id: str = typer.Argument(..., help="Skill ID to update"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm updates for external skills"),
    allow_network: bool = typer.Option(
        False, "--allow-network", help="Allow network access for updates"
    ),
) -> None:
    """Update an installed skill to the latest catalog version."""
    try:
        entry = catalog_find(skill_id)
        if entry is None:
            get_console().print(f"[red]Skill '{skill_id}' not found in catalog.[/red]")
            raise typer.Exit(1)

        if not is_installed(skill_id):
            get_console().print(
                f"[yellow]Skill '{skill_id}' is not installed. Use 'add' to install.[/yellow]"
            )
            raise typer.Exit(1)

        get_console().print(f"[bold]Updating {entry.name}...[/bold]")
        record = update_entry(
            skill_id,
            entry,
            allow_external=yes,
            network_enabled=allow_network,
        )
        get_console().print(f"[green]Updated {record.id} to v{record.version or 'latest'}[/green]")
    except PermissionError as exc:
        get_console().print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def skills_info_cmd(
    skill_id: str = typer.Argument(..., help="Skill ID to show details for"),
) -> None:
    """Show details about a catalog skill."""
    try:
        entry = catalog_find(skill_id)
        if entry is None:
            get_console().print(f"[red]Skill '{skill_id}' not found in catalog.[/red]")
            raise typer.Exit(1)

        get_console().print(f"\n[bold cyan]{entry.name}[/bold cyan] ({entry.id})")
        get_console().print(f"  Kind:      {entry.kind.value}")
        get_console().print(f"  Trust:     {entry.trust.value}")
        get_console().print(f"  Summary:   {entry.summary}")
        if entry.source_url:
            get_console().print(f"  Source:    {entry.source_url}")
        if entry.version:
            get_console().print(f"  Version:   {entry.version}")
        if entry.tags:
            get_console().print(f"  Tags:      {', '.join(entry.tags)}")
        get_console().print(f"  Network:   {'Yes' if entry.requires_network else 'No'}")
        if entry.install_hint:
            get_console().print(f"  Install:   {entry.install_hint}")

        if is_installed(skill_id):
            get_console().print("\n  [green]Status: Installed[/green]")
        else:
            get_console().print("\n  [dim]Status: Not installed[/dim]")
        get_console().print()
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
