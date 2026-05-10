"""MCP discovery management commands."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from rich.markup import escape
from rich.table import Table
import typer

from beep.config import load_config
from beep.mcp.discovery import (
    resolve_mcp_configuration,
    update_managed_mcp_server_tools,
    write_mcp_server_definition,
)
from beep.mcp.live_discovery import discover_verified_tool_contracts
from beep.mcp.presets import get_mcp_preset, list_mcp_presets
from beep.mcp.tool_contracts import build_verified_tool_metadata, parse_verified_tool_contracts
from beep.workspace.detector import find_workspace_root
from beep.utils.console import get_console


def mcp_list_cmd() -> None:
    """List configured and auto-discovered MCP server definitions."""
    console = get_console()
    workspace_root = find_workspace_root()
    resolved = resolve_mcp_configuration(load_config(), workspace_root)

    if not resolved.servers:
        console.print("[yellow]No MCP server definitions found[/yellow]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Transport", style="magenta")
    table.add_column("Target", style="green")
    table.add_column("Tools", justify="right")
    table.add_column("Source", overflow="fold")
    for server in resolved.servers:
        table.add_row(
            server.name,
            server.transport,
            _format_mcp_server_target(server),
            str(len(server.tools)),
            resolved.sources.get(server.name, "unknown"),
        )
    console.print(table)
    if resolved.errors:
        console.print("\n[yellow]Discovery warnings:[/yellow]")
        for warning in resolved.errors:
            console.print(f"  - {warning}")


def mcp_presets_cmd() -> None:
    """List the built-in verified MCP launch presets."""
    console = get_console()
    table = Table(title="MCP Presets")
    table.add_column("Preset", style="cyan")
    table.add_column("Launch", style="green")
    table.add_column("Tools", justify="right")
    table.add_column("Required env")
    table.add_column("Docs", overflow="fold")
    for preset in list_mcp_presets():
        command, args = preset.resolved_launch()
        table.add_row(
            preset.key,
            " ".join([command, *args]).strip(),
            str(len(preset.tools)),
            ", ".join(preset.required_env) or "-",
            preset.docs_url,
        )
    console.print(table)
    console.print(
        "[dim]Presets always store verified launch metadata. Verified static tool schemas are included only when the vendor docs or source publish them explicitly.[/dim]"
    )


def mcp_init_cmd(
    name: str = typer.Argument(..., help="Server name"),
    command: str | None = typer.Option(
        None,
        "--command",
        help="Executable used to start the MCP server. Required unless --preset is used.",
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        help="Streamable HTTP MCP endpoint. Use instead of --command or --preset.",
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="Create the server definition from a verified built-in preset.",
    ),
    arg: list[str] | None = typer.Option(None, "--arg", help="Repeat for each command argument"),
    env: list[str] | None = typer.Option(
        None, "--env", help="Repeat KEY=VALUE pairs for server environment"
    ),
    header: list[str] | None = typer.Option(
        None,
        "--header",
        help="Repeat KEY=VALUE pairs for streamable HTTP request headers.",
    ),
    scope: str = typer.Option("workspace", "--scope", help="workspace or user"),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing managed server definition"
    ),
) -> None:
    """Create a managed MCP server definition file for auto-discovery."""
    console = get_console()
    workspace_root = find_workspace_root()
    server_config = None
    try:
        env_map = _parse_env_pairs(env)
        header_map = _parse_env_pairs(header)
        metadata = None
        missing_required_env: list[str] = []
        transport = "stdio"
        target_url: str | None = None

        selected_targets = [value for value in (preset, command, url) if value]
        if len(selected_targets) != 1:
            raise ValueError("Choose exactly one of --preset, --command, or --url.")

        if preset:
            preset_definition = get_mcp_preset(preset)
            server_config, metadata, missing_required_env = (
                preset_definition.build_server_definition(
                    name=name,
                    env_overrides=env_map,
                    extra_args=list(arg or []),
                )
            )
            command = server_config.command
            args = server_config.args
            env_map = server_config.env
            header_map = server_config.headers
            transport = server_config.transport
            target_url = server_config.url
        else:
            args = list(arg or [])
            if url:
                transport = "http"
                target_url = url
                if args:
                    raise ValueError("--arg is only valid with stdio MCP servers.")
                if env_map:
                    raise ValueError("--env is only valid with stdio MCP servers.")
            elif header_map:
                raise ValueError("--header is only valid with streamable HTTP MCP servers.")

        file_path = write_mcp_server_definition(
            workspace_root,
            name=name,
            transport=transport,
            command=command,
            args=args,
            env=env_map,
            url=target_url,
            headers=header_map,
            tools=server_config.tools if preset else None,
            metadata=metadata,
            scope=scope,
            force=force,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except FileExistsError as exc:
        console.print(f"[red]Server definition already exists: {exc}[/red]")
        raise typer.Exit(1)
    except OSError as exc:
        console.print(f"[red]Failed to write MCP server definition: {exc}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Created MCP server definition:[/green] {file_path}")
    if preset:
        console.print(f"[dim]Preset:[/dim] {preset}")
        if server_config.tools:
            console.print(f"[dim]Verified tool contracts:[/dim] {len(server_config.tools)}")
        if missing_required_env:
            missing_env = ", ".join(missing_required_env)
            console.print(
                f"[yellow]Required environment values were not written:[/yellow] {missing_env}. "
                "Provide them with --env KEY=VALUE or set them in the environment used to launch Beep."
            )
    console.print(
        "[dim]Note: launch metadata is always stored. Tool declarations are only written when their schemas are verified from vendor documentation or source.[/dim]"
    )


def mcp_verify_tools_cmd(
    name: str = typer.Argument(..., help="Managed MCP server name"),
    from_file: str | None = typer.Option(
        None,
        "--from-file",
        help="JSON file containing verified tool contracts, or omit to read from stdin when --discover is not used.",
    ),
    discover: bool = typer.Option(
        False,
        "--discover",
        help="Launch the named MCP server and fetch verified tool contracts via a live tools/list request.",
    ),
) -> None:
    """Validate and persist verified MCP tool contracts for a managed server definition."""
    console = get_console()
    workspace_root = find_workspace_root()
    config = load_config()
    try:
        if discover:
            if from_file is not None:
                raise ValueError("Use either --discover or --from-file, not both.")
            server = _resolve_named_mcp_server(name=name, workspace_root=workspace_root, config=config)
            discovery_result = asyncio.run(discover_verified_tool_contracts(server))
            tools = discovery_result.tools
            source_label = f"live:{server.name}"
            metadata_updates = build_verified_tool_metadata(
                source=source_label,
                tools=tools,
                protocol_version=discovery_result.protocol_version,
                server_info=discovery_result.server_info,
            )
        else:
            raw_payload, source_label = _read_tool_contract_payload(from_file or "-")
            payload = json.loads(raw_payload)
            tools = parse_verified_tool_contracts(payload)
            metadata_updates = build_verified_tool_metadata(source=source_label, tools=tools)
        file_path = update_managed_mcp_server_tools(
            workspace_root,
            name=name,
            tools=tools,
            metadata_updates=metadata_updates,
            config=config,
        )
    except json.JSONDecodeError as exc:
        console.print(
            f"[red]{escape(f'Invalid JSON tool-contract payload: {exc}')}[/red]",
            soft_wrap=True,
        )
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("[yellow]Live MCP tool discovery cancelled[/yellow]")
        raise typer.Exit(1)
    except (FileNotFoundError, OSError, ValueError) as exc:
        console.print(f"[red]{escape(str(exc))}[/red]", soft_wrap=True)
        raise typer.Exit(1)

    console.print(f"[green]Verified MCP tool contracts updated:[/green] {file_path}")
    console.print(f"[dim]Tool contracts persisted:[/dim] {len(tools)}")
    console.print(f"[dim]Verification source:[/dim] {source_label}")


def _read_tool_contract_payload(from_file: str) -> tuple[str, str]:
    source_text = str(from_file).strip() or "-"
    if source_text == "-":
        payload = sys.stdin.read()
        if not payload.strip():
            raise ValueError("Expected verified tool-contract JSON on stdin")
        return payload, "stdin"

    file_path = Path(source_text)
    payload = file_path.read_text(encoding="utf-8")
    if not payload.strip():
        raise ValueError(f"Verified tool-contract file is empty: {file_path}")
    return payload, str(file_path)


def _parse_env_pairs(pairs: list[str] | None) -> dict[str, str]:
    env: dict[str, str] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"Invalid --env value '{pair}'. Use KEY=VALUE.")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid --env value '{pair}'. Use KEY=VALUE.")
        env[key] = value
    return env


def _format_mcp_server_target(server: object) -> str:
    transport = getattr(server, "transport", "stdio")
    if transport == "http":
        return str(getattr(server, "url", "") or "")
    command = str(getattr(server, "command", "") or "")
    args = [str(arg) for arg in getattr(server, "args", [])]
    return " ".join([command, *args]).strip()


def _resolve_named_mcp_server(*, name: str, workspace_root: Path, config) -> object:
    resolved = resolve_mcp_configuration(config, workspace_root)
    for server in resolved.servers:
        if server.name == name:
            return server
    raise FileNotFoundError(f"Managed MCP server '{name}' was not found")
