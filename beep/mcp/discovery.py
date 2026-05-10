"""File-backed MCP server discovery helpers."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from beep.config import BeepConfig, MCPServerConfig, MCPToolConfig


@dataclass(frozen=True)
class DiscoveredMcpServer:
    """A discovered MCP server entry and its source."""

    config: MCPServerConfig
    source: str


@dataclass(frozen=True)
class ResolvedMcpConfiguration:
    """The resolved MCP configuration used by CLI and agent entrypoints."""

    enabled: bool
    servers: list[MCPServerConfig]
    sources: dict[str, str]
    errors: list[str]


def resolve_mcp_configuration(
    config: BeepConfig,
    workspace_root: Path | None = None,
) -> ResolvedMcpConfiguration:
    """Merge persisted config with discovered MCP server definitions."""
    resolved_root = workspace_root.resolve() if workspace_root is not None else Path.cwd().resolve()
    discovered, errors = discover_mcp_servers(resolved_root)

    merged: dict[str, MCPServerConfig] = {}
    sources: dict[str, str] = {}
    for server in discovered:
        merged[server.config.name] = server.config
        sources[server.config.name] = server.source
    for server in config.mcp_servers:
        merged[server.name] = server
        sources[server.name] = "config"

    servers = list(merged.values())
    return ResolvedMcpConfiguration(
        enabled=bool(config.mcp_enabled or servers),
        servers=servers,
        sources=sources,
        errors=errors,
    )


def discover_mcp_servers(workspace_root: Path) -> tuple[list[DiscoveredMcpServer], list[str]]:
    """Discover MCP server declarations from managed directories and config files."""
    discovered: list[DiscoveredMcpServer] = []
    errors: list[str] = []

    for json_file in _iter_server_definition_files(workspace_root):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            discovered.extend(_extract_server_entries(payload, json_file))
        except (OSError, json.JSONDecodeError, ValueError, ValidationError) as exc:
            errors.append(f"{json_file}: {exc}")

    return discovered, errors


def get_managed_mcp_directory(workspace_root: Path, *, scope: str = "workspace") -> Path:
    """Return the managed MCP server directory for the chosen scope."""
    if scope == "user":
        return Path.home() / ".beepai" / "mcp"
    if scope == "workspace":
        return workspace_root / ".beep" / "mcp"
    raise ValueError("scope must be 'user' or 'workspace'")


def write_mcp_server_definition(
    workspace_root: Path,
    *,
    name: str,
    transport: str = "stdio",
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    url: str | None = None,
    headers: dict[str, str] | None = None,
    tools: list[MCPToolConfig] | None = None,
    metadata: dict[str, Any] | None = None,
    scope: str = "workspace",
    force: bool = False,
) -> Path:
    """Write a managed MCP server definition file for auto-discovery."""
    directory = get_managed_mcp_directory(workspace_root, scope=scope)
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"{_slugify(name)}.json"
    if file_path.exists() and not force:
        raise FileExistsError(file_path)

    config = MCPServerConfig(
        name=name,
        transport=transport,
        command=command,
        args=list(args or []),
        env=dict(env or {}),
        url=url,
        headers=dict(headers or {}),
        tools=list(tools or []),
    )
    payload = config.model_dump(exclude_none=True)
    if metadata:
        payload["metadata"] = metadata
    file_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return file_path


def update_managed_mcp_server_tools(
    workspace_root: Path,
    *,
    name: str,
    tools: list[MCPToolConfig],
    metadata_updates: dict[str, Any] | None = None,
    config: BeepConfig | None = None,
) -> Path:
    """Replace the tool contracts for an existing managed MCP definition."""
    file_path = resolve_managed_mcp_server_definition_path(
        workspace_root,
        name=name,
        config=config,
    )
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Managed MCP definition must be a JSON object: {file_path}")

    payload["tools"] = [tool.model_dump(exclude_none=True) for tool in tools]
    metadata = payload.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError(f"Managed MCP definition metadata must be a JSON object: {file_path}")
    if metadata_updates:
        metadata.update(metadata_updates)
    payload["metadata"] = metadata

    validation_payload = dict(payload)
    validation_payload.pop("metadata", None)
    MCPServerConfig.model_validate(validation_payload)

    file_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return file_path


def resolve_managed_mcp_server_definition_path(
    workspace_root: Path,
    *,
    name: str,
    config: BeepConfig | None = None,
) -> Path:
    """Return the writable managed definition path for a discovered MCP server."""
    resolved = resolve_mcp_configuration(config or BeepConfig(), workspace_root)
    source = resolved.sources.get(name)
    if source is None:
        raise FileNotFoundError(name)
    if source == "config":
        raise ValueError(
            f"MCP server '{name}' comes from the main config file and cannot be updated with managed tool verification. Recreate it with `beep mcp init` first."
        )
    source_path = Path(source)
    managed_roots = {
        get_managed_mcp_directory(workspace_root, scope="workspace").resolve(),
        get_managed_mcp_directory(workspace_root, scope="user").resolve(),
    }
    try:
        source_parent = source_path.parent.resolve()
    except OSError as exc:
        raise ValueError(f"Unable to resolve MCP server definition path for '{name}': {source_path}") from exc
    if source_parent not in managed_roots:
        raise ValueError(
            f"MCP server '{name}' is not backed by a managed .beep MCP definition and cannot be updated in place: {source}"
        )
    return source_path


def _iter_server_definition_files(workspace_root: Path) -> list[Path]:
    files: list[Path] = []
    files.extend(_iter_json_files(Path.home() / ".beepai" / "mcp"))

    env_dir = os.environ.get("BEEP_MCP_DIR")
    if env_dir:
        files.extend(_iter_json_files(Path(env_dir)))

    files.extend(_iter_json_files(workspace_root / ".beep" / "mcp"))

    vscode_config = workspace_root / ".vscode" / "mcp.json"
    if vscode_config.exists():
        files.append(vscode_config)

    return files


def _iter_json_files(directory: Path) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.json") if path.is_file())


def _extract_server_entries(payload: Any, source_path: Path) -> list[DiscoveredMcpServer]:
    if isinstance(payload, dict) and "name" in payload and any(
        key in payload for key in ("command", "url", "serverUrl", "endpoint")
    ):
        return [
            DiscoveredMcpServer(
                config=MCPServerConfig.model_validate(payload),
                source=str(source_path),
            )
        ]

    if not isinstance(payload, dict):
        raise ValueError("server definition must be a JSON object")

    for key in ("servers", "mcpServers"):
        mapping = payload.get(key)
        if isinstance(mapping, dict):
            return [
                DiscoveredMcpServer(
                    config=_build_server_config(name, raw_server),
                    source=str(source_path),
                )
                for name, raw_server in mapping.items()
            ]
        if isinstance(mapping, list):
            return [
                DiscoveredMcpServer(
                    config=_build_server_config(None, raw_server),
                    source=str(source_path),
                )
                for raw_server in mapping
            ]

    raw_servers = payload.get("mcp_servers")
    if isinstance(raw_servers, list):
        return [
            DiscoveredMcpServer(
                config=_build_server_config(None, raw_server),
                source=str(source_path),
            )
            for raw_server in raw_servers
        ]

    raise ValueError("unsupported MCP server definition format")


def _build_server_config(name: str | None, raw_server: Any) -> MCPServerConfig:
    if not isinstance(raw_server, dict):
        raise ValueError("server entries must be JSON objects")

    payload = dict(raw_server)
    if name and "name" not in payload:
        payload["name"] = name

    return MCPServerConfig.model_validate(payload)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip().lower()).strip("-")
    return slug or "mcp-server"