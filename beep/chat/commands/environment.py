"""Environment and local session control slash commands."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command



from beep.utils.console import get_console
class HooksCommand(Command):
    @property
    def name(self) -> str:
        return "hooks"

    @property
    def description(self) -> str:
        return "Manage pre/post hooks"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        from beep.hooks.manager import load_hooks, save_hooks

        config = load_hooks()

        if not args:
            if not config.hooks:
                get_console().print("[yellow]No hooks configured[/yellow]")
                return
            get_console().print("[bold]Hooks:[/bold]")
            for i, h in enumerate(config.hooks):
                status = "[green]on[/green]" if h.enabled else "[red]off[/red]"
                get_console().print(f"  {i}. [{h.event}] {h.command} {status}")
            return

        parts = args.split(maxsplit=2)
        action = parts[0].lower()

        if action == "add" and len(parts) >= 3:
            config.add(parts[1], parts[2])
            save_hooks(config)
            get_console().print(f"[green]Hook added: {parts[1]} -> {parts[2]}[/green]")
        elif action == "remove" and len(parts) >= 2:
            if config.remove(int(parts[1])):
                save_hooks(config)
                get_console().print("[green]Hook removed[/green]")
        elif action == "toggle" and len(parts) >= 2:
            if config.toggle(int(parts[1])):
                save_hooks(config)
                get_console().print("[green]Hook toggled[/green]")
        else:
            get_console().print(
                "[yellow]Usage: /hooks | /hooks add <event> <cmd> | "
                "/hooks remove <n> | /hooks toggle <n>[/yellow]"
            )


class InstallCommand(Command):
    @property
    def name(self) -> str:
        return "install"

    @property
    def description(self) -> str:
        return "Auto-detect and install dependencies"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        import asyncio

        from beep.workspace.detector import find_workspace_root

        root = find_workspace_root()
        packages = args.split() if args else []

        if (root / "requirements.txt").exists():
            get_console().print("[dim]Installing from requirements.txt...[/dim]")
            proc = await asyncio.create_subprocess_exec(
                "pip",
                "install",
                "-r",
                "requirements.txt",
                cwd=root,
            )
            await proc.wait()
        elif (root / "package.json").exists():
            get_console().print("[dim]Installing from package.json...[/dim]")
            proc = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                cwd=root,
            )
            await proc.wait()
        elif packages:
            get_console().print(f"[dim]Installing: {', '.join(packages)}[/dim]")
            proc = await asyncio.create_subprocess_exec(
                "pip",
                "install",
                *packages,
            )
            await proc.wait()
        else:
            get_console().print("[yellow]No dependency file found. Usage: /install <packages>[/yellow]")


class SandboxCommand(Command):
    @property
    def name(self) -> str:
        return "sandbox"

    @property
    def description(self) -> str:
        return "Show or set sandbox mode"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        from beep.permissions.manager import SandboxMode, coerce_sandbox_mode

        session = ctx["session"]
        current_mode = getattr(session, "_sandbox_mode", SandboxMode.WORKSPACE_WRITE)
        raw = args.strip()

        if not raw or raw.lower() == "status":
            get_console().print(f"Sandbox mode: [cyan]{current_mode.value}[/cyan]")
            return

        try:
            new_mode = coerce_sandbox_mode(raw)
        except ValueError:
            get_console().print("[yellow]Usage: /sandbox status | read-only | workspace-write | full-trust[/yellow]")
            return

        session._sandbox_mode = new_mode
        session._sandbox = new_mode == SandboxMode.READ_ONLY
        get_console().print(f"Sandbox mode: [cyan]{new_mode.value}[/cyan]")


class MaxTokensCommand(Command):
    @property
    def name(self) -> str:
        return "max_tokens"

    @property
    def description(self) -> str:
        return "Set session token budget"

    @property
    def category(self) -> str:
        return "General"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            session = ctx["session"]
            budget = getattr(session, "_max_token_budget", "unlimited")
            get_console().print(f"Token budget: [cyan]{budget}[/cyan]")
            return

        try:
            limit = int(args)
            ctx["session"]._max_token_budget = limit
            get_console().print(f"[green]Token budget: {limit:,}[/green]")
        except ValueError:
            get_console().print("[yellow]Usage: /max_tokens <number>[/yellow]")
