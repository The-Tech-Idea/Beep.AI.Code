"""Session-owned runtime state helpers for chat commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SessionMcpRuntimeState:
    """Resolved MCP runtime owned by a chat session."""

    owner: str = "chat-session"
    resolution: Any | None = None
    client: Any | None = None
    resolution_error: str | None = None
    client_error: str | None = None


def get_session_task_manager(session: Any) -> Any:
    """Get or create the task manager owned by a chat session."""
    manager = getattr(session, "_task_manager", None)
    if manager is None:
        from beep.app_service import get_app_service

        manager = get_app_service().tasks
        setattr(session, "_task_manager", manager)
    return manager


def get_session_watcher(session: Any) -> Any:
    """Get or create the watcher owned by a chat session."""
    watcher = getattr(session, "_watcher", None)
    if watcher is None:
        from beep.app_service import get_app_service

        watcher = get_app_service().watcher(session._workspace)
        setattr(session, "_watcher", watcher)
    return watcher


def get_session_mcp_runtime(session: Any, *, refresh: bool = False) -> SessionMcpRuntimeState:
    """Get or create the MCP runtime owned by a chat session."""
    state = getattr(session, "_mcp_runtime_state", None)
    if state is None or refresh:
        state = refresh_session_mcp_runtime(session)
    return state


def refresh_session_mcp_runtime(session: Any) -> SessionMcpRuntimeState:
    """Resolve MCP configuration and client state for the active session."""
    config = getattr(session, "_config", None)
    workspace_root = getattr(session, "_workspace", None)
    if config is None or workspace_root is None:
        state = SessionMcpRuntimeState()
        setattr(session, "_mcp_runtime_state", state)
        return state

    try:
        from beep.mcp.discovery import resolve_mcp_configuration

        resolved = resolve_mcp_configuration(config, workspace_root)
    except Exception as exc:
        state = SessionMcpRuntimeState(resolution_error=str(exc))
        setattr(session, "_mcp_runtime_state", state)
        return state

    client = None
    client_error = None
    if resolved.servers:
        try:
            from beep.app_service import get_app_service

            client = get_app_service().mcp_client(resolved.servers)
        except Exception as exc:
            client_error = str(exc)

    state = SessionMcpRuntimeState(
        resolution=resolved,
        client=client,
        client_error=client_error,
    )
    setattr(session, "_mcp_runtime_state", state)
    return state


def clear_session_runtime_state(session: Any) -> None:
    """Clear task, watcher, and edit runtime state for a chat session."""
    task_manager = getattr(session, "_task_manager", None)
    if task_manager is not None and hasattr(task_manager, "cancel_all"):
        task_manager.cancel_all()
    setattr(session, "_task_manager", None)

    watcher = getattr(session, "_watcher", None)
    if watcher is not None:
        watcher.stop()
    setattr(session, "_watcher", None)

    setattr(session, "_mcp_runtime_state", None)

    session._edit_target = None
    session._last_edit = None
