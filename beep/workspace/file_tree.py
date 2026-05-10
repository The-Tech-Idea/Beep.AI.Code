"""File tree display."""

from __future__ import annotations

from pathlib import Path

from rich.tree import Tree

from beep.workspace.ignore import IgnoreMatcher


from beep.utils.console import get_console
DEFAULT_IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    "*.egg-info",
}


def build_tree(
    directory: Path,
    tree: Tree,
    matcher: IgnoreMatcher | None = None,
    max_depth: int = 5,
    current_depth: int = 0,
) -> None:
    """Recursively build a Rich tree from directory structure."""
    if current_depth >= max_depth:
        return

    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return

    for entry in entries:
        if matcher is not None and matcher.is_ignored(entry):
            continue

        if entry.is_dir():
            branch = tree.add(f"[bold blue]{entry.name}/[/bold blue]")
            build_tree(entry, branch, matcher, max_depth, current_depth + 1)
        else:
            tree.add(f"[green]{entry.name}[/green]")


def display_tree(
    workspace_root: Path,
    *,
    max_depth: int = 3,
    show_all: bool = False,
) -> None:
    """Display workspace file tree.

    Args:
        workspace_root: Root directory
        max_depth: Maximum depth to display
        show_all: Show ignored files
    """
    if show_all:
        matcher = IgnoreMatcher(workspace_root, patterns=[])
    else:
        matcher = IgnoreMatcher(workspace_root)

    tree = Tree(f"[bold]{workspace_root.name}[/bold]")
    build_tree(workspace_root, tree, matcher, max_depth)

    get_console().print(tree)
