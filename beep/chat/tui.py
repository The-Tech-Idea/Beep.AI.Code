"""Terminal UI components for the Beep.AI.Code chat REPL.

Provides profile-aware status bars, agent panels, layer listings,
and command palette rendering using Rich.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def render_profile_status(profile_info: dict[str, str]) -> Panel:
    """Render a compact profile status line.

    Args:
        profile_info: Dict with keys: icon, name, model, server, tier
    """
    icon = profile_info.get("icon", "🤖")
    name = profile_info.get("name", "No profile")
    model = profile_info.get("model", "default")
    server = profile_info.get("server", "")
    tier = profile_info.get("tier", "")

    parts = [
        f"{icon} [bold]{name}[/bold]",
        f"[dim]Model: {model}[/dim]",
    ]
    if tier:
        tier_colors = {"great": "green", "good": "blue", "basic": "yellow", "minimal": "red"}
        color = tier_colors.get(tier, "dim")
        parts.append(f"[{color}]Tier: {tier}[/{color}]")

    return Panel(
        "  |  ".join(parts),
        border_style="blue",
        padding=(0, 1),
    )


def render_agent_switched(old_agent: str, new_agent: str, layer_id: str | None = None) -> str:
    """Render an agent switch notification."""
    layer_info = f" (layer: {layer_id})" if layer_id else ""
    return (
        f"[bold green]✓[/bold green] Switched from "
        f"[dim]{old_agent}[/dim] → [bold cyan]{new_agent}[/bold cyan]{layer_info}"
    )


def render_agent_list(agents: list[dict[str, str]], active_id: str = "") -> Table:
    """Render available agents as a table.

    Args:
        agents: List of dicts with: id, name, description, layer
        active_id: Currently active agent ID (gets highlighted)
    """
    table = Table(title="Available Agents", border_style="blue", show_header=True)
    table.add_column("", width=2)
    table.add_column("Agent", style="cyan")
    table.add_column("Description", style="dim")
    table.add_column("Layer", style="yellow")

    for agent in agents:
        mark = "[bold green]●[/bold green]" if agent["id"] == active_id else "○"
        name = f"[bold]{agent['name']}[/bold]" if agent["id"] == active_id else agent["name"]
        table.add_row(
            mark,
            name,
            agent.get("description", ""),
            agent.get("layer", "—"),
        )

    return table


def render_layer_list(layers: list[dict[str, str]]) -> Table:
    """Render available specialty layers as a table.

    Args:
        layers: List of dicts with: id, name, type, domain, description, enabled
    """
    table = Table(title="Specialty Layers", border_style="blue", show_header=True)
    table.add_column("Status", width=6)
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Domain", style="green")
    table.add_column("Description", style="dim")

    for layer in layers:
        status = "[green]✓[/green]" if layer.get("enabled", True) else "[red]✗[/red]"
        table.add_row(
            status,
            layer["name"],
            layer.get("type", ""),
            layer.get("domain", ""),
            layer.get("description", ""),
        )

    return table


def render_command_help(commands: dict[str, str]) -> Panel:
    """Render available slash commands as a panel.

    Args:
        commands: Dict mapping command name to description
    """
    lines: list[str] = []
    for cmd, desc in sorted(commands.items()):
        lines.append(f"[bold cyan]/{cmd}[/bold cyan]  [dim]— {desc}[/dim]")

    return Panel(
        "\n".join(lines),
        title="Commands",
        border_style="blue",
    )


def render_profile_summary(profile: Any) -> Panel:
    """Render a full profile summary panel."""
    if profile is None:
        return Panel(
            "[yellow]No profile configured.[/yellow]\n"
            "Run [bold]beep setup-profile[/bold] to set up your AI experience.",
            title="Profile",
            border_style="yellow",
        )

    lines = [
        f"{profile.profile_icon} [bold]{profile.profile_display_name}[/bold]",
        f"[dim]ID: {profile.profile_id}[/dim]",
        f"[dim]Server: {profile.server_url}[/dim]",
        f"[dim]Model: {profile.model.model_id}[/dim]",
    ]
    if hasattr(profile, "created_services") and profile.created_services:
        svc = ", ".join(profile.created_services[:3])
        if len(profile.created_services) > 3:
            svc += f" +{len(profile.created_services) - 3} more"
        lines.append(f"[dim]Services: {svc}[/dim]")

    return Panel(
        "\n".join(lines),
        title="Active Profile",
        border_style="green",
    )


def render_startup_banner(profile: Any, workspace: str, model: str, session_id: str) -> str:
    """Render the startup welcome banner."""
    icon = getattr(profile, "profile_icon", "🤖") if profile else "🤖"
    name = getattr(profile, "profile_display_name", "Beep.AI.Code") if profile else "Beep.AI.Code"
    profile_id = getattr(profile, "profile_id", "") if profile else ""

    lines = [
        f"{icon}  [bold blue]{name}[/bold blue]",
        f"[dim]Workspace: {workspace}[/dim]",
        f"[dim]Model: {model}[/dim]",
        f"[dim]Session: {session_id[:12]}...[/dim]",
    ]
    if profile_id:
        lines.insert(1, f"[dim]Profile: {profile_id}[/dim]")

    return "\n".join(lines)
