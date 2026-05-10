"""Workspace root detection."""

from __future__ import annotations

from pathlib import Path


def find_workspace_root(start: Path | None = None) -> Path:
    """Find the workspace root directory.

    Walks up from the current directory looking for a .git directory.
    Falls back to the current directory if not found.

    Args:
        start: Starting directory (defaults to cwd)

    Returns:
        Workspace root path
    """
    current = start or Path.cwd()
    current = current.resolve()
    home = Path.home()

    for directory in [current] + list(current.parents):
        if (directory / ".git").exists():
            return directory
        if directory == home:
            break

    return current


def get_relative_path(path: Path, workspace_root: Path) -> str:
    """Get path relative to workspace root."""
    try:
        return str(path.relative_to(workspace_root))
    except ValueError:
        return str(path)
