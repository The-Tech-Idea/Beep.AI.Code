"""Diff generation for edit tracking."""

from __future__ import annotations

import difflib


def generate_diff(original: str, modified: str, path: str, context_lines: int = 3) -> str:
    """Generate a unified diff between original and modified content."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=context_lines,
    )
    return "".join(diff)


def count_changed_lines(diff_text: str) -> tuple[int, int]:
    """Count added and removed lines from a unified diff."""
    added = 0
    removed = 0
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return added, removed
