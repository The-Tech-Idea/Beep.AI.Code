"""Runtime collection and rendering helpers for diagnostics and doctor commands."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from rich.table import Table
from beep.utils.console import get_console


def collect_agent_runtime_status() -> dict[str, object]:
    from beep.agent.environment import AgentEnvironmentManager

    return AgentEnvironmentManager().status()


def collect_diagnostics_state(
    *,
    inspect_config_schema: Callable[[Path], dict[str, object]] | Callable[..., dict[str, object]],
    collect_agent_runtime_status: Callable[[], dict[str, object]],
    inspect_session_history_schema: Callable[[Path], dict[str, object]]
    | Callable[..., dict[str, object]],
    inspect_workspace_session_memory_schema: Callable[[Path], dict[str, object]]
    | Callable[..., dict[str, object]],
    build_repair_guidance: Callable[..., list[str]],
) -> dict[str, object]:
    from beep import __version__
    from beep.config import CONFIG_FILE, CONFIG_SCHEMA_VERSION, load_config
    from beep.mcp.discovery import resolve_mcp_configuration
    from beep.memory.agent import AgentMemory
    from beep.plugins.runtime import load_runtime_plugins
    from beep.sessions.history import HISTORY_DIR, SESSION_HISTORY_SCHEMA_VERSION
    from beep.utils.json_logging import is_json_logging_enabled
    from beep.workspace.detector import find_workspace_root
    from beep.workspace.git import is_git_repo

    config = load_config()
    workspace = Path(find_workspace_root())
    config_schema = inspect_config_schema(CONFIG_FILE, expected_schema=CONFIG_SCHEMA_VERSION)
    agent_runtime = collect_agent_runtime_status()
    history_schema = inspect_session_history_schema(
        HISTORY_DIR,
        expected_schema=SESSION_HISTORY_SCHEMA_VERSION,
    )
    session_memory_schema = inspect_workspace_session_memory_schema(
        workspace,
        expected_schema=AgentMemory._SCHEMA_VERSION,
    )
    repair_guidance = build_repair_guidance(
        config=config,
        config_schema=config_schema,
        agent_runtime=agent_runtime,
        history_schema=history_schema,
        session_memory_schema=session_memory_schema,
    )
    plugin_runtime = load_runtime_plugins(workspace, enabled=True)
    resolved_mcp = resolve_mcp_configuration(config, workspace)
    return {
        "version": __version__,
        "config": config,
        "workspace": workspace,
        "config_file": CONFIG_FILE,
        "is_git_repo": is_git_repo(workspace),
        "json_logging_enabled": is_json_logging_enabled(),
        "config_schema": config_schema,
        "agent_runtime": agent_runtime,
        "history_schema": history_schema,
        "session_memory_schema": session_memory_schema,
        "repair_guidance": repair_guidance,
        "plugin_runtime": plugin_runtime,
        "resolved_mcp": resolved_mcp,
    }


def render_diagnostics_state(state: dict[str, object]) -> None:
    config = state["config"]
    workspace = state["workspace"]
    config_file = state["config_file"]
    config_schema = state["config_schema"]
    agent_runtime = state["agent_runtime"]
    history_schema = state["history_schema"]
    session_memory_schema = state["session_memory_schema"]
    repair_guidance = state["repair_guidance"]
    plugin_runtime = state["plugin_runtime"]
    resolved_mcp = state["resolved_mcp"]

    get_console().print("[bold]Beep.AI.Code Diagnostics[/bold]\n")

    get_console().print(f"Version: {state['version']}")
    get_console().print(f"Python: {sys.version}")
    get_console().print(f"Config: {config_file}")
    get_console().print(f"Configured: {'Yes' if config.is_configured else 'No'}")
    get_console().print(f"Server: {config.server_url}")
    get_console().print(f"Workspace: {workspace}")
    get_console().print(f"Git repo: {'Yes' if state['is_git_repo'] else 'No'}")
    get_console().print(f"Default model: {config.default_model or '(server default)'}")
    get_console().print(f"Max tokens: {config.max_tokens}")
    get_console().print(f"Temperature: {config.temperature}")
    get_console().print(f"MCP bridge enabled: {'Yes' if resolved_mcp.enabled else 'No'}")
    get_console().print(f"MCP servers available: {len(resolved_mcp.servers)}")
    get_console().print(f"JSON logging: {'Yes' if state['json_logging_enabled'] else 'No'}")

    doctor_table = Table(title="Doctor Summary")
    doctor_table.add_column("Surface", style="cyan")
    doctor_table.add_column("Status", style="green")
    doctor_table.add_column("Details", overflow="fold")
    doctor_table.add_row(
        "Config Schema",
        str(config_schema.get("status", "unknown")),
        str(config_schema.get("reason", "None")),
    )
    doctor_table.add_row(
        "Agent Runtime",
        str(agent_runtime.get("compatibility_status") or agent_runtime.get("status") or "unknown"),
        str(
            agent_runtime.get("repair_reason")
            or agent_runtime.get("compatibility_reason")
            or "None"
        ),
    )
    doctor_table.add_row(
        "Session History",
        str(history_schema.get("status", "unknown")),
        str(history_schema.get("reason", "None")),
    )
    doctor_table.add_row(
        "Workspace Session Memory",
        str(session_memory_schema.get("status", "unknown")),
        str(session_memory_schema.get("reason", "None")),
    )
    get_console().print(doctor_table)

    get_console().print(f"Plugins loaded: {getattr(plugin_runtime, 'loaded_count', 0)}")
    get_console().print("Plugin search paths:")
    for path in getattr(plugin_runtime, "searched_paths", []):
        get_console().print(f"  - {path}")
    load_errors = plugin_runtime.registry.get_load_errors()
    if load_errors:
        get_console().print("Plugin load errors:")
        for err in load_errors:
            get_console().print(f"  - {err}")
    else:
        get_console().print("Plugin load errors: none")
    if getattr(plugin_runtime, "discovery_errors", None):
        get_console().print("Plugin discovery warnings:")
        for err in plugin_runtime.discovery_errors:
            get_console().print(f"  - {err}")
    if getattr(resolved_mcp, "errors", None):
        get_console().print("MCP discovery warnings:")
        for err in resolved_mcp.errors:
            get_console().print(f"  - {err}")

    deps = {
        "typer": "typer",
        "rich": "rich",
        "httpx": "httpx",
        "textual": "textual",
        "pygments": "pygments",
    }

    get_console().print("\n[bold]Dependencies:[/bold]")
    for name, module in deps.items():
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            get_console().print(f"  {name}: {version}")
        except ImportError:
            get_console().print(f"  {name}: [red]not installed[/red]")

    get_console().print("\n[bold]Repair Guidance:[/bold]")
    for item in repair_guidance:
        get_console().print(f"  - {item}")


def supported_auto_repairs(state: dict[str, object]) -> list[tuple[str, Callable[[], None]]]:
    from beep.commands.agent import agent_reinstall_cmd, agent_setup_cmd

    agent_runtime = state["agent_runtime"]
    repair_command = str(agent_runtime.get("repair_command") or "").strip()
    repairs: list[tuple[str, Callable[[], None]]] = []
    if repair_command == "beep agent setup":
        repairs.append(("managed agent runtime refresh", agent_setup_cmd))
    elif repair_command == "beep agent reinstall runtime":
        repairs.append(("managed agent runtime rebuild", lambda: agent_reinstall_cmd("runtime")))
    return repairs


def doctor_has_manual_issues(state: dict[str, object]) -> bool:
    config = state["config"]
    config_schema = state["config_schema"]
    history_schema = state["history_schema"]
    session_memory_schema = state["session_memory_schema"]
    if not bool(getattr(config, "is_configured", False)):
        return True
    if str(config_schema.get("status") or "current") in {"corrupt", "unsupported"}:
        return True
    if str(history_schema.get("status") or "current") in {"corrupt", "unsupported"}:
        return True
    if str(session_memory_schema.get("status") or "absent") in {"corrupt", "unsupported"}:
        return True
    return False
