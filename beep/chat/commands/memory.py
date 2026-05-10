"""Memory-related slash commands."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command


from beep.utils.console import get_console


class MemoryReloadCommand(Command):
    """Reload project memory and workspace rules from disk."""

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Manage project memory. /memory reload — reload .beep.md, rules, and server skills from disk"

    @property
    def category(self) -> str:
        return "System"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        sub = args.strip().lower()
        if sub not in ("", "reload"):
            get_console().print("[yellow]Usage: /memory reload[/yellow]")
            return

        from beep.chat.command_registry import build_custom_command_registry
        from beep.runtime.workspace import clear_workspace_runtime_cache, get_workspace_runtime
        from beep.skills.resolver import SkillResolver

        clear_workspace_runtime_cache()
        session = ctx.get("session")
        if session is None:
            get_console().print("[green]Cache cleared. Memory will reload on next action.[/green]")
            return

        workspace = getattr(session, "_workspace", None)
        plugins_enabled = getattr(session, "_plugins_enabled", True)
        if workspace is None:
            get_console().print("[green]Cache cleared. Memory will reload on next action.[/green]")
            return

        runtime = get_workspace_runtime(workspace, plugins_enabled=plugins_enabled)
        session._memory = runtime.memory
        session._rules = runtime.rules
        session._rule_errors = runtime.rule_errors
        session._skills = list(runtime.skills)
        session._skill_errors = runtime.skill_errors
        session._skill_roots = runtime.skill_roots

        # Re-merge server skills (re-fetch from server)
        try:
            client = ctx.get("client")
            if client is not None:
                from beep.api.client_workspace_support import fetch_server_skills
                from beep.skills.loader import server_skills_to_definitions

                server_skills = await fetch_server_skills(client)
                if server_skills:
                    remote_defs = server_skills_to_definitions(server_skills)
                    local_names = {s.name for s in runtime.skills}
                    for s in remote_defs:
                        if s.name not in local_names:
                            session._skills.append(s)
        except Exception:
            pass  # Server skills are optional

        session._skill_resolver = SkillResolver(session._skills)

        # Rebuild command registry with updated custom commands
        base_commands = dict(runtime.commands)
        custom = build_custom_command_registry(runtime.memory.commands)
        base_commands.update(custom)
        session._commands = base_commands

        get_console().print("[green]Memory reloaded.[/green]")
        if runtime.memory.global_instructions:
            get_console().print(
                f"[dim]Project instructions: {len(runtime.memory.global_instructions)} chars[/dim]"
            )
        if runtime.memory.commands:
            get_console().print(
                f"[dim]Custom commands: {list(runtime.memory.commands.keys())}[/dim]"
            )
        if runtime.rules:
            get_console().print(f"[dim]Rules: {len(runtime.rules)} loaded[/dim]")
