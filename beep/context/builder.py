"""Context builder for injecting workspace info into prompts."""

from __future__ import annotations

from pathlib import Path

from beep.workspace.detector import find_workspace_root, get_relative_path
from beep.workspace.binary_detector import is_binary_file
from beep.workspace.file_ops import read_file
from beep.workspace.ignore import IgnoreMatcher

MAX_FILE_SIZE = 50_000
MAX_CONTEXT_FILES = 10


def build_context(
    files: list[Path],
    workspace_root: Path | None = None,
) -> str:
    """Build context string from files.

    Args:
        files: List of file paths to include
        workspace_root: Workspace root (auto-detected if None)

    Returns:
        Formatted context string for prompt injection
    """
    root = workspace_root or find_workspace_root()
    matcher = IgnoreMatcher(root)
    parts = []
    omitted: list[str] = []

    for i, file_path in enumerate(files):
        if i >= MAX_CONTEXT_FILES:
            # Collect all remaining files as omitted.
            for remaining in files[i:]:
                rel = str(get_relative_path(remaining, root))
                omitted.append(rel)
            break

        if not file_path.exists() or not file_path.is_file():
            continue

        if matcher.is_ignored(file_path):
            continue

        if file_path.stat().st_size > MAX_FILE_SIZE:
            size = file_path.stat().st_size
            rel = get_relative_path(file_path, root)
            parts.append(f"## {rel} (file too large, {size} bytes)")
            continue

        if is_binary_file(file_path):
            parts.append(f"## {get_relative_path(file_path, root)} (binary, skipped)")
            continue

        try:
            content = read_file(file_path, show_numbers=True, highlight=False)
            rel_path = get_relative_path(file_path, root)
            parts.append(f"## {rel_path}\n```\n{content}\n```")
        except (OSError, UnicodeDecodeError):
            parts.append(f"## {get_relative_path(file_path, root)} (could not read)")

    if not parts:
        return ""

    header = "Here is the relevant code context:\n\n"
    body = "\n\n".join(parts)
    if omitted:
        omit_notice = (
            f"\n\n<!-- context limit reached: {len(omitted)} file(s) omitted: "
            + ", ".join(omitted)
            + " -->"
        )
        return header + body + omit_notice
    return header + body


def get_workspace_summary(workspace_root: Path | None = None) -> str:
    """Get a summary of the workspace.

    Returns:
        Summary string with file counts and structure
    """
    root = workspace_root or find_workspace_root()
    matcher = IgnoreMatcher(root)

    file_count = 0
    dir_count = 0

    for path in root.rglob("*"):
        if matcher.is_ignored(path):
            continue
        if path.is_file():
            file_count += 1
        elif path.is_dir():
            dir_count += 1

    return f"Workspace: {root.name}\nFiles: {file_count}\nDirectories: {dir_count}"
