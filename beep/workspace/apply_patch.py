"""Unified diff parser and applier.

Parses and applies unified diff patches with safety checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Hunk:
    """A single hunk in a unified diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]


@dataclass
class Patch:
    """A parsed unified diff patch."""

    old_path: str
    new_path: str
    hunks: list[Hunk]


def parse_patch(diff: str) -> Patch:
    """Parse a unified diff string into a Patch object."""
    lines = diff.splitlines()
    old_path = ""
    new_path = ""
    hunks: list[Hunk] = []
    current_hunk: list[str] = []
    hunk_header: tuple[int, int, int, int] | None = None

    for line in lines:
        if line.startswith("--- "):
            old_path = line[4:].lstrip("a/")
        elif line.startswith("+++ "):
            new_path = line[4:].lstrip("b/")
        elif line.startswith("@@ "):
            if hunk_header and current_hunk:
                hunks.append(Hunk(*hunk_header, current_hunk))
                current_hunk = []
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2) or "1")
                new_start = int(match.group(3))
                new_count = int(match.group(4) or "1")
                hunk_header = (old_start, old_count, new_start, new_count)
        elif hunk_header is not None:
            current_hunk.append(line)

    if hunk_header and current_hunk:
        hunks.append(Hunk(*hunk_header, current_hunk))

    return Patch(old_path=old_path, new_path=new_path, hunks=hunks)


def apply_patch(content: str, diff: str) -> str | None:
    """Apply a unified diff to content.

    Returns the patched content or None if the patch fails.
    """
    patch = parse_patch(diff)
    if not patch.hunks:
        return None

    orig_lines = content.splitlines(keepends=True)
    ensured = [
        line if line.endswith("\n") else line + "\n"
        for line in orig_lines
    ]

    offset = 0
    for hunk in patch.hunks:
        old_start = hunk.old_start - 1 + offset
        hunk_lines = hunk.lines

        context_lines: list[str] = []
        replacement_lines: list[str] = []

        for hline in hunk_lines:
            if hline.startswith(" "):
                context_lines.append(hline[1:])
                replacement_lines.append(hline[1:])
            elif hline.startswith("-"):
                context_lines.append(hline[1:])
            elif hline.startswith("+"):
                replacement_lines.append(hline[1:])
            elif hline.startswith("\\"):
                pass

        start = old_start
        end = old_start + len(context_lines)

        if start < 0 or end > len(ensured):
            return None

        existing = ensured[start:end]
        expected = [
            line if line.endswith("\n") else line + "\n"
            for line in context_lines
        ]

        if existing != expected:
            return None

        new_lines = [
            line if line.endswith("\n") else line + "\n"
            for line in replacement_lines
        ]

        ensured[start:end] = new_lines
        offset += len(new_lines) - len(context_lines)

    result = "".join(ensured)
    if not result.endswith("\n") and content.endswith("\n"):
        result += "\n"
    return result


def apply_patch_file(path: Path, diff: str) -> tuple[bool, str]:
    """Apply a patch file.

    Returns (success, message).
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"Cannot read file: {e}"

    result = apply_patch(content, diff)
    if result is None:
        return False, "Patch could not be applied (context mismatch)"

    path.write_text(result, encoding="utf-8")
    return True, f"Patch applied to {path}"
