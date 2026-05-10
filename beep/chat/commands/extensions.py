"""Plugin, skill, and rule inspection slash commands."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command


from beep.utils.console import get_console


class PluginsCommand(Command):
    @property
    def name(self) -> str:
        return "plugins"

    @property
    def description(self) -> str:
        return "List loaded plugins and load issues"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        runtime = ctx.get("plugin_runtime")
        if runtime is None:
            get_console().print("[yellow]Plugin runtime unavailable[/yellow]")
            return

        searched = runtime.searched_paths
        if searched:
            get_console().print("[bold]Plugin search paths:[/bold]")
            for path in searched:
                get_console().print(f"  - {path}")

        plugins = runtime.registry.list_plugins()
        if plugins:
            get_console().print("\n[bold]Loaded plugins:[/bold]")
            for plugin in plugins:
                get_console().print(
                    f"  - {plugin['name']} v{plugin['version']} "
                    f"({plugin['type']}) - {plugin['description']}"
                )
        else:
            get_console().print("\n[yellow]No plugins loaded[/yellow]")

        errors = runtime.registry.get_load_errors()
        if errors:
            get_console().print("\n[bold red]Load errors:[/bold red]")
            for error in errors:
                get_console().print(f"  - {error}")


class SkillsCommand(Command):
    @property
    def name(self) -> str:
        return "skills"

    @property
    def description(self) -> str:
        return "List loaded skills and status"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        enabled = getattr(session, "_skills_enabled", True)
        status = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
        get_console().print(f"Skills: {status}")

        roots = getattr(session, "_skill_roots", [])
        if roots:
            get_console().print("[bold]Skill search paths:[/bold]")
            for root in roots:
                get_console().print(f"  - {root}")

        skills = getattr(session, "_skills", [])
        if skills:
            local_skills = [s for s in skills if not s.source.startswith("server:")]
            remote_skills = [s for s in skills if s.source.startswith("server:")]
            get_console().print("\n[bold]Loaded skills:[/bold]")
            for skill in local_skills:
                triggers = ", ".join(skill.triggers) if skill.triggers else "none"
                get_console().print(
                    f"  - {skill.name} (priority={skill.priority}, inject={skill.inject}, "
                    f"triggers={triggers})"
                )
            if remote_skills:
                get_console().print("\n[bold dim]Server skills (global):[/bold dim]")
                for skill in remote_skills:
                    triggers = ", ".join(skill.triggers) if skill.triggers else "none"
                    get_console().print(
                        f"  - {skill.name} (priority={skill.priority}, inject={skill.inject}, "
                        f"triggers={triggers})"
                    )
        else:
            get_console().print("\n[yellow]No skills loaded[/yellow]")

        errors = getattr(session, "_skill_errors", [])
        if errors:
            get_console().print("\n[bold red]Load errors:[/bold red]")
            for error in errors:
                get_console().print(f"  - {error}")


class SkillCommand(Command):
    @property
    def name(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        return "Control skills: /skill on|off"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        action = args.strip().lower()
        if action == "off":
            session._skills_enabled = False
            get_console().print("[yellow]Skills disabled for this session[/yellow]")
            return
        if action == "on":
            session._skills_enabled = True
            get_console().print("[green]Skills enabled for this session[/green]")
            return
        get_console().print("[yellow]Usage: /skill on | /skill off[/yellow]")


class RulesCommand(Command):
    @property
    def name(self) -> str:
        return "rules"

    @property
    def description(self) -> str:
        return "Show active rule sources"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        rules = getattr(session, "_rules", [])
        if not rules:
            get_console().print("[yellow]No rules loaded[/yellow]")
            return
        get_console().print("[bold]Active rules (load order):[/bold]")
        for idx, rule in enumerate(rules, start=1):
            applies = f" applies_to={rule.applies_to}" if rule.applies_to else ""
            get_console().print(f"  {idx}. {rule.source}{applies}")

        errors = getattr(session, "_rule_errors", [])
        if errors:
            get_console().print("\n[bold red]Rule load errors:[/bold red]")
            for error in errors:
                get_console().print(f"  - {error}")
