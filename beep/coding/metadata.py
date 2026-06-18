"""Build Beep.AI.Server Coding Assistant request metadata.

Includes specialty layer context so the server can augment the
agent's system prompt with domain-specific knowledge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_coding_metadata(
    *,
    workspace_root: Path | str,
    interaction_mode: str,
    project_id: int | None = None,
    session_id: str | None = None,
    use_layer_id: str | None = None,
    active_agent_id: str | None = None,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Return the canonical coding_assistant envelope for CLI requests.

    Includes specialty layer and agent context so the server can:
    - Apply layer-specific system prompt augmentation (RAG, tools, domain knowledge)
    - Route to the correct agent template
    - Apply profile-appropriate guardrails
    """
    metadata: dict[str, Any] = {
        "workspace_root": str(workspace_root),
        "interaction_mode": interaction_mode,
    }
    if project_id is not None:
        metadata["project_id"] = project_id
    if session_id:
        metadata["session_id"] = session_id

    # ── Layer-aware context ──────────────────────────────────────────
    if use_layer_id:
        metadata["use_layer_id"] = use_layer_id
    if active_agent_id:
        metadata["active_agent_id"] = active_agent_id
    if profile_id:
        metadata["profile_id"] = profile_id

    return metadata
