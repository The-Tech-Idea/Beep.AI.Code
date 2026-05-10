"""Tab completion for file paths in REPL."""

from __future__ import annotations

from pathlib import Path

from beep.workspace.detector import find_workspace_root
from beep.workspace.ignore import IgnoreMatcher


def complete_path(partial: str, workspace_root: Path | None = None) -> list[str]:
    """Complete a partial file path.

    Returns list of possible completions.
    """
    root = workspace_root or find_workspace_root()
    matcher = IgnoreMatcher(root)

    if not partial:
        return []

    partial_path = Path(partial)
    is_absolute = partial_path.is_absolute()

    if is_absolute:
        search_root = partial_path.parent if partial_path.parent.exists() else Path("/")
        prefix = str(partial_path.parent) + "/"
    else:
        search_root = root / partial_path.parent if partial_path.parent != Path(".") else root
        prefix = str(partial_path.parent) + "/" if partial_path.parent != Path(".") else ""
        if prefix == "./":
            prefix = ""

    if not search_root.exists():
        return []

    partial_name = partial_path.name.lower()
    completions = []

    try:
        for entry in search_root.iterdir():
            if matcher.is_ignored(entry):
                continue
            if entry.name.lower().startswith(partial_name):
                if entry.is_dir():
                    completions.append(prefix + entry.name + "/")
                else:
                    completions.append(prefix + entry.name)
    except PermissionError:
        pass

    return sorted(completions)


def complete_command(partial: str, commands: dict[str, str]) -> list[str]:
    """Complete a slash command."""
    if not partial.startswith("/"):
        return []
    cmd = partial[1:].lower()
    return [
        f"/{name}" for name in commands
        if name.lower().startswith(cmd)
    ]
