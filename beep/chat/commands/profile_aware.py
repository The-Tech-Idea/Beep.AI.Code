"""Profile-aware slash commands for the chat REPL.

Provides /agent, /agents, /layers, and /profile slash commands
that integrate with the AgentRoster and LayerCatalog.
"""

from __future__ import annotations

from typing import Any

from beep.chat.commands.base import Command
from beep.chat.tui import (
    render_agent_list,
    render_agent_switched,
    render_command_help,
    render_layer_list,
    render_profile_summary,
)
from beep.utils.console import get_console


class AgentCommand(Command):
    """Switch active agent: /agent <name|id>"""

    name = "agent"
    description = "Switch to a different agent (e.g., /agent code_reviewer)"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        console = get_console()

        if not args.strip():
            # Show current agent
            try:
                from beep.profiles.agent_roster import get_agent_roster
                roster = get_agent_roster()
                if roster.active:
                    console.print(f"[bold]Active:[/bold] {roster.active.display_name}")
                    console.print(f"[dim]{roster.active.description}[/dim]")
                else:
                    console.print("[yellow]No agent active. Run /agents to see available agents.[/yellow]")
            except ImportError:
                console.print("[red]Agent roster not available.[/red]")
            return

        agent_id = args.strip()
        try:
            from beep.profiles.agent_roster import get_agent_roster
            roster = get_agent_roster()
            old_name = roster.active.display_name if roster.active else "none"
            new_ctx = roster.activate(agent_id)
            if new_ctx is None:
                console.print(f"[red]Agent not found: {agent_id}[/red]")
                console.print("[dim]Use /agents to see available agents.[/dim]")
                return
            console.print(render_agent_switched(old_name, new_ctx.display_name, new_ctx.layer_id))
        except ImportError:
            console.print("[red]Agent roster not available. Run 'beep setup-profile' first.[/red]")


class AgentsCommand(Command):
    """List available agents: /agents"""

    name = "agents"
    description = "List all available agents for your profile"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        console = get_console()
        try:
            from beep.profiles.agent_roster import get_agent_roster
            roster = get_agent_roster()
            agents = roster.list_agents()
            if not agents:
                console.print("[yellow]No agents available.[/yellow]")
                console.print("[dim]Run 'beep setup-profile' to create agents.[/dim]")
                return

            active_id = roster.active.agent_id if roster.active else ""
            agent_dicts = [
                {
                    "id": a.agent_id,
                    "name": a.display_name,
                    "description": a.description,
                    "layer": a.layer_id or "—",
                }
                for a in agents
            ]
            console.print(render_agent_list(agent_dicts, active_id))
            console.print("[dim]Use /agent <name> to switch agents.[/dim]")
        except ImportError:
            console.print("[red]Agent roster not available.[/red]")


class LayersCommand(Command):
    """List available specialty layers: /layers"""

    name = "layers"
    description = "List available specialty layers from the server"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        console = get_console()
        try:
            from beep.profiles.layer_catalog import get_layer_catalog
            catalog = get_layer_catalog()
            if not catalog.is_loaded:
                console.print("[yellow]Layer catalog not loaded.[/yellow]")
                console.print("[dim]Layers are fetched from the server on agent startup.[/dim]")
                return

            layers = catalog.all_layers()
            if not layers:
                console.print("[yellow]No layers available.[/yellow]")
                return

            layer_dicts = [
                {
                    "id": l.id,
                    "name": l.name,
                    "type": l.type,
                    "domain": l.domain,
                    "description": l.description,
                    "enabled": l.enabled,
                }
                for l in layers
            ]
            console.print(render_layer_list(layer_dicts))
            console.print(f"[dim]{len(layers)} layers loaded from server.[/dim]")
        except ImportError:
            console.print("[red]Layer catalog not available.[/red]")


class ProfileCommand(Command):
    """Show profile info: /profile"""

    name = "profile"
    description = "Show your active profile and settings"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        console = get_console()
        try:
            from beep.profiles import has_saved_profile, load_active_profile
            if not has_saved_profile():
                console.print("[yellow]No profile configured.[/yellow]")
                console.print("[dim]Run 'beep setup-profile' to set up your AI experience.[/dim]")
                return
            profile = load_active_profile()
            console.print(render_profile_summary(profile))
        except ImportError:
            console.print("[red]Profiles not available.[/red]")


def register_profile_commands(commands: dict[str, Command]) -> None:
    """Register profile-aware slash commands into the command dict."""
    commands["/agent"] = AgentCommand()
    commands["/agents"] = AgentsCommand()
    commands["/layers"] = LayersCommand()
    commands["/profile"] = ProfileCommand()
