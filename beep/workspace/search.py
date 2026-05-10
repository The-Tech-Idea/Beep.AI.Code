"""Shared workspace regex search helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from beep.workspace.ignore import IgnoreMatcher


@dataclass(frozen=True)
class WorkspaceSearchMatch:
    relative_path: Path
    line_number: int
    line_text: str
    is_match: bool = True


@dataclass(frozen=True)
class WorkspaceSearchResult:
    matches: tuple[WorkspaceSearchMatch, ...]
    capped: bool = False


def compile_search_pattern(pattern: str, *, case_sensitive: bool) -> re.Pattern[str]:
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"Invalid regex: {exc}") from exc


def search_workspace(
    root: Path,
    *,
    pattern: str,
    case_sensitive: bool = True,
    file_pattern: str | None = None,
    context_lines: int = 0,
    max_results: int | None = None,
) -> WorkspaceSearchResult:
    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"Not a directory: {resolved_root}")

    regex = compile_search_pattern(pattern, case_sensitive=case_sensitive)
    matcher = IgnoreMatcher(resolved_root)
    normalized_context = max(context_lines, 0)
    matches: list[WorkspaceSearchMatch] = []
    seen_context_lines: set[tuple[Path, int]] = set()
    capped = False

    for file_path in sorted(resolved_root.rglob("*")):
        if not file_path.is_file() or matcher.is_ignored(file_path):
            continue
        if file_pattern and not file_path.match(file_pattern):
            continue

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = file_path.relative_to(resolved_root)
        for line_number, line_text in enumerate(lines, 1):
            if not regex.search(line_text):
                continue

            start = max(1, line_number - normalized_context)
            end = min(len(lines), line_number + normalized_context)
            for current_line in range(start, end + 1):
                if normalized_context and (file_path, current_line) in seen_context_lines:
                    continue
                if normalized_context:
                    seen_context_lines.add((file_path, current_line))
                matches.append(
                    WorkspaceSearchMatch(
                        relative_path=rel_path,
                        line_number=current_line,
                        line_text=lines[current_line - 1],
                        is_match=current_line == line_number,
                    )
                )
                if max_results is not None and len(matches) >= max_results:
                    capped = True
                    break
            if capped:
                break
        if capped:
            break

    return WorkspaceSearchResult(matches=tuple(matches), capped=capped)