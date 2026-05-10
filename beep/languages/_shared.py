"""Shared helpers for language adapters."""

from __future__ import annotations

import json
from pathlib import Path


def has_tool(tool_name: str) -> bool:
    """Check if a command-line tool is available."""
    import shutil

    return shutil.which(tool_name) is not None


def read_package_json(root: Path) -> dict | None:
    """Read and parse package.json if it exists."""
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return None
    try:
        return json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def relative_path(workspace_root: Path, file_path: Path) -> str:
    """Return file_path relative to workspace_root, or absolute if outside."""
    try:
        return str(file_path.relative_to(workspace_root))
    except ValueError:
        return str(file_path)


def deduplicate(paths: list[str]) -> list[str]:
    """Deduplicate file paths while preserving order."""
    return list(dict.fromkeys(paths))
