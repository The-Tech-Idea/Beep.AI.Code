"""Build Beep.AI.Server Coding Assistant request metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_coding_metadata(
    *,
    workspace_root: Path | str,
    interaction_mode: str,
    project_id: int | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Return the canonical coding_assistant envelope for CLI requests."""
    metadata: dict[str, Any] = {
        "workspace_root": str(workspace_root),
        "interaction_mode": interaction_mode,
    }
    if project_id is not None:
        metadata["project_id"] = project_id
    if session_id:
        metadata["session_id"] = session_id
    return metadata
