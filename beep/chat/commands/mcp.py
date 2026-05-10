"""MCP slash command — inspect MCP bridge tools and servers."""

from __future__ import annotations

from typing import Any

from rich.table import Table

from beep.chat.commands.base import Command



from beep.utils.console import get_console
class McpCommand(Command):
    """Inspect the MCP bridge: list servers and available tools."""

    @property
    def name(self) -> str:
        return "mcp"

    @property
    def description(self) -> str:
        return "Inspect MCP bridge: /mcp status | /mcp tools | /mcp servers"

    @property
    def category(self) -> str:
        return "Integration"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        sub = args.strip().split()[0].lower() if args.strip() else "tools"

        mcp_runtime = ctx.get("mcp_runtime")
        mcp_client = ctx.get("mcp_client")
        mcp_resolution = ctx.get("mcp_resolution")

        if sub == "status":
            self._show_status(mcp_runtime, mcp_client, mcp_resolution)
        elif sub == "servers":
            self._show_servers(mcp_runtime, mcp_client, mcp_resolution)
        else:
            self._show_tools(mcp_runtime, mcp_client)

    def _show_status(self, mcp_runtime: Any, mcp_client: Any, mcp_resolution: Any) -> None:
        resolution = getattr(mcp_runtime, "resolution", None) or mcp_resolution
        client = getattr(mcp_runtime, "client", None) or mcp_client
        resolution_error = getattr(mcp_runtime, "resolution_error", None)
        client_error = getattr(mcp_runtime, "client_error", None)
        owner = getattr(mcp_runtime, "owner", "command-context") if mcp_runtime is not None else "command-context"

        if resolution is None and resolution_error is None and client is None:
            get_console().print("[yellow]MCP runtime not configured for this session.[/yellow]")
            return

        t = Table(title="MCP Status", show_lines=True)
        t.add_column("Property", style="cyan")
        t.add_column("Value", overflow="fold")
        t.add_row("Owner", owner)
        t.add_row("Bridge enabled", "Yes" if bool(getattr(resolution, "enabled", False)) else "No")
        t.add_row("Server definitions", str(len(getattr(resolution, "servers", []) if resolution is not None else [])))
        t.add_row("Available tools", str(len(client.list_tools()) if client is not None else 0))
        t.add_row(
            "Client status",
            "ready" if client is not None else ("error" if client_error else "inactive"),
        )
        get_console().print(t)

        if resolution_error:
            get_console().print(f"[red]Resolution error:[/red] {resolution_error}")
        if client_error:
            get_console().print(f"[red]Client error:[/red] {client_error}")
        if resolution is not None and getattr(resolution, "errors", None):
            get_console().print("[yellow]Discovery warnings:[/yellow]")
            for warning in resolution.errors:
                get_console().print(f"  - {warning}")

    def _show_servers(self, mcp_runtime: Any, mcp_client: Any, mcp_resolution: Any) -> None:
        resolution = getattr(mcp_runtime, "resolution", None) or mcp_resolution
        client = getattr(mcp_runtime, "client", None) or mcp_client
        client_error = getattr(mcp_runtime, "client_error", None)

        if resolution is None and client is None:
            get_console().print("[yellow]MCP bridge not active in this session.[/yellow]")
            return

        if resolution is not None:
            servers = getattr(resolution, "servers", [])
            sources = getattr(resolution, "sources", {})
            if not servers:
                get_console().print("[yellow]No MCP servers registered.[/yellow]")
                return
            t = Table(title="MCP Servers", show_lines=True)
            t.add_column("Server", style="cyan")
            t.add_column("Source", overflow="fold")
            t.add_column("Client", style="dim")
            for server in servers:
                t.add_row(
                    server.name,
                    sources.get(server.name, "unknown"),
                    "ready" if client is not None else ("error" if client_error else "definition-only"),
                )
            get_console().print(t)
            if client_error:
                get_console().print(f"[red]Client error:[/red] {client_error}")
            return

        servers = client.list_servers() if client is not None else []
        if not servers:
            get_console().print("[yellow]No MCP servers registered.[/yellow]")
            return
        t = Table(title="MCP Servers", show_lines=True)
        t.add_column("Server", style="cyan")
        for name in servers:
            t.add_row(name)
        get_console().print(t)

    def _show_tools(self, mcp_runtime: Any, mcp_client: Any) -> None:
        client = getattr(mcp_runtime, "client", None) or mcp_client
        client_error = getattr(mcp_runtime, "client_error", None)
        if client is None:
            if client_error:
                get_console().print(f"[red]MCP client unavailable:[/red] {client_error}")
                return
            get_console().print("[yellow]MCP bridge not active in this session.[/yellow]")
            return
        tools = client.list_tools()
        if not tools:
            get_console().print("[yellow]No MCP tools available.[/yellow]")
            return
        t = Table(title="MCP Tools", show_lines=True)
        t.add_column("Tool", style="cyan")
        t.add_column("Server", style="dim")
        t.add_column("Read-only", style="green")
        t.add_column("Approval", style="yellow")
        t.add_column("Description")
        for tool in tools:
            t.add_row(
                tool.name,
                tool.server_name,
                "Yes" if bool(getattr(tool, "read_only_safe", False)) else "No",
                (
                    "Required"
                    if bool(getattr(tool, "requires_human_approval", True))
                    else "Not required"
                ),
                tool.description,
            )
        get_console().print(t)
