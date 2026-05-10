"""Coding Assistant bridge helpers for interactive chat."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from beep.api.client import BeepAPIClient
from beep.utils.json_logging import log_event

if TYPE_CHECKING:
    from rich.console import Console


async def bootstrap_coding_workspace(
    client: BeepAPIClient,
    *,
    workspace: Path,
    config: Any,
    model: str | None,
    console: Console,
) -> tuple[int | None, str | None]:
    """Resolve Coding Assistant project/session IDs for chat."""
    configured_project_id = getattr(config, "project_id", None)
    if configured_project_id:
        result = await client.bootstrap_project(
            configured_project_id,
            interaction_mode="inline",
            model_id=model,
        )
    else:
        result = await client.bootstrap_workspace(
            workspace_root=str(workspace),
            create_project_if_missing=True,
            create_session_if_missing=True,
            model_id=model,
        )

    if not result.get("success"):
        console.print(f"[dim]Coding assistant unavailable: {result.get('error', 'unknown')}[/dim]")
        log_event("coding.bootstrap.unavailable", error=result.get("error", "unknown"))
        return None, None

    project_id = result.get("project_id") or configured_project_id
    session_id = result.get("session_id")
    transport = result.get("transport", {})
    if transport.get("session_id"):
        session_id = transport["session_id"]

    console.print(f"[dim]Connected: project {project_id}, session {session_id}[/dim]")
    log_event("coding.bootstrap.success", project_id=project_id, session_id=session_id)
    return project_id, session_id
