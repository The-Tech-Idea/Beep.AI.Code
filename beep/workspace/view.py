"""Shared workspace file and tree viewing helpers."""

from __future__ import annotations

from pathlib import Path

from beep.workspace.file_ops import read_file
from beep.workspace.file_tree import display_tree


def read_workspace_file(
    path: str | Path,
    *,
    start_line: int | None = None,
    end_line: int | None = None,
    show_numbers: bool = True,
    highlight: bool = True,
) -> str:
    """Read a workspace file with shared validation and formatting."""
    file_path = Path(path)
    if not file_path.exists():
        raise ValueError(f"File not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Not a file: {path}")

    try:
        return read_file(
            file_path,
            start_line=start_line,
            end_line=end_line,
            show_numbers=show_numbers,
            highlight=highlight,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to read file: {exc}") from exc


def show_workspace_tree(
    path: str | Path,
    *,
    max_depth: int = 3,
    show_all: bool = False,
) -> None:
    """Display a workspace tree with shared validation."""
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {path}")

    try:
        display_tree(root, max_depth=max_depth, show_all=show_all)
    except Exception as exc:
        raise RuntimeError(f"Failed to display tree: {exc}") from exc