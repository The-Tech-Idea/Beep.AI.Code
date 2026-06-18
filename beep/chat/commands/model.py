"""Model and AI settings commands: /model, /mode, /tokens, /cost, /permissions."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from beep.chat.commands.base import Command


from beep.utils.console import get_console


class ModelCommand(Command):
    @property
    def name(self) -> str:
        return "model"

    @property
    def description(self) -> str:
        return "List and select a model"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        client = ctx["client"]

        if args:
            session.set_model(args)
            get_console().print(f"[green]Model: {args}[/green]")
            return

        get_console().print("[dim]Fetching models...[/dim]")
        try:
            models = await client.list_models()
        except Exception as exc:
            get_console().print(f"[red]Failed: {e}[/red]")
            cur = session._model or "(default)"
            get_console().print(f"Current: [cyan]{cur}[/cyan]")
            return

        if not models:
            cur = session._model or "(default)"
            get_console().print(f"Current: [cyan]{cur}[/cyan]")
            get_console().print("[yellow]No models from server[/yellow]")
            return

        table = Table(title="Available Models")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Model ID", style="cyan")
        table.add_column("Owned By", style="dim")

        current = session._model or ""
        for i, m in enumerate(models, 1):
            mid = m.get("id", "unknown")
            owned = m.get("owned_by", "")
            marker = " [green]*[/green]" if mid == current else ""
            table.add_row(str(i), mid + marker, owned)

        get_console().print(table)

        choice = Prompt.ask("\nSelect model (number or name)", default="0")
        try:
            idx = int(choice)
            if idx == 0:
                get_console().print(f"[dim]Keeping: {current or '(default)'}[/dim]")
            elif 1 <= idx <= len(models):
                selected = models[idx - 1]["id"]
                session.set_model(selected)
                get_console().print(f"[green]Model: {selected}[/green]")
            else:
                get_console().print("[red]Invalid[/red]")
        except ValueError:
            if choice.strip():
                session.set_model(choice.strip())
                get_console().print(f"[green]Model: {choice.strip()}[/green]")


class ModeCommand(Command):
    @property
    def name(self) -> str:
        return "mode"

    @property
    def description(self) -> str:
        return "Switch mode (assistant|review|explain)"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        valid = {"assistant", "review", "explain"}

        if args:
            if args not in valid:
                get_console().print(f"[yellow]Valid: {', '.join(sorted(valid))}[/yellow]")
                return
            session.set_mode(args)
            get_console().print(f"[green]Mode: {args}[/green]")
        else:
            get_console().print(f"Mode: [cyan]{session._mode}[/cyan]  ({'|'.join(sorted(valid))})")


class TokensCommand(Command):
    @property
    def name(self) -> str:
        return "tokens"

    @property
    def description(self) -> str:
        return "Toggle token display"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        session._show_tokens = not session._show_tokens
        status = "on" if session._show_tokens else "off"
        get_console().print(f"[green]Token display: {status}[/green]")


class CostCommand(Command):
    @property
    def name(self) -> str:
        return "cost"

    @property
    def description(self) -> str:
        return "Show token usage and estimated cost"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        est = session._token_count
        model = getattr(session, "_model", None)
        from beep.chat.pricing import estimate_cost, price_hint

        cost = estimate_cost(est, model)
        hint = price_hint(model)
        budget = getattr(session, "_max_token_budget", None)
        budget_info = (
            f"Budget: [cyan]{budget:,} tokens[/cyan] ([yellow]{((est / budget) * 100):.1f}% used[/yellow])"
            if budget and budget > 0
            else "Budget: [dim]unlimited[/dim]"
        )

        get_console().print(
            Panel(
                f"Model: [cyan]{model or 'default'}[/cyan]\n"
                f"Pricing: [dim]{hint}[/dim]\n"
                f"Requests: [cyan]{session._request_count}[/cyan]\n"
                f"Est. tokens: [cyan]{est:,}[/cyan]\n"
                f"Est. cost: [green]${cost:.4f}[/green]\n"
                f"{budget_info}\n"
                f"Messages: [cyan]{len(session._messages)}[/cyan]",
                title="Usage",
                border_style="blue",
            )
        )


class PermissionsCommand(Command):
    @property
    def name(self) -> str:
        return "permissions"

    @property
    def description(self) -> str:
        return "Show permission settings"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, _args: str, _ctx: dict[str, Any]) -> None:
        from beep.app_service import get_app_service

        pm = get_app_service().permissions
        get_console().print(
            Panel(
                pm.to_prompt_section(),
                title="Permissions",
                border_style="yellow",
            )
        )
