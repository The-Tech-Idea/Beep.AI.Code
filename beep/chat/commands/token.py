"""Token check command: /token."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command



from beep.utils.console import get_console
class TokenCommand(Command):
    @property
    def name(self) -> str:
        return "token"

    @property
    def description(self) -> str:
        return "Check API token"

    @property
    def category(self) -> str:
        return "System"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        client = ctx.get("client")
        if not client:
            get_console().print("[red]No API client[/red]")
            return

        if args.lower() == "check":
            try:
                result = await client.check_token()
                if result.get("valid"):
                    get_console().print("[green]Token is valid[/green]")
                    app = result.get("application", {})
                    if app:
                        get_console().print(
                            f"[dim]Application: {app.get('name', 'unknown')}[/dim]"
                        )
                    scopes = result.get("scopes", [])
                    if scopes:
                        get_console().print(f"[dim]Scopes: {', '.join(scopes)}[/dim]")
                else:
                    get_console().print(f"[red]Token is invalid: {result.get('error')}[/red]")
            except Exception as exc:
                get_console().print(f"[red]Token check failed: {e}[/red]")
        else:
            get_console().print("[yellow]Usage: /token check[/yellow]")
