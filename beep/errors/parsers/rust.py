"""Rust error output parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_RUST_ERROR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"-->\s+([^:\s]+\.rs):(\d+):(\d+)"),
    re.compile(r"error\[[\w\d]+\]:\s+(.*?)(?=\n\n|\nerror|\nwarning|$)", re.DOTALL),
    re.compile(r"panicked at\s+([^:\s]+\.rs):(\d+):(\d+)"),
    re.compile(r"thread\s+.*?panicked at\s+([^:\s]+\.rs):(\d+):(\d+)"),
]


def parse_rust_errors(output: str) -> list[ParsedError]:
    """Extract error locations from Rust compiler/test output."""
    results: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()

    for pattern in _RUST_ERROR_PATTERNS:
        for match in pattern.finditer(output):
            groups = match.groups()
            file_path = groups[0] if len(groups) > 0 and groups[0].endswith(".rs") else None
            line_str = groups[1] if len(groups) > 1 else None
            column_str = groups[2] if len(groups) > 2 else None

            if file_path is None:
                file_match = re.search(
                    r"-->\s+([^:\s]+\.rs)", output[max(0, match.start() - 50) : match.start()]
                )
                if file_match:
                    file_path = file_match.group(1)

            try:
                line = int(line_str) if line_str else None
            except ValueError:
                continue
            try:
                column = int(column_str) if column_str else None
            except ValueError:
                column = None

            key = (file_path, line)
            if key in seen:
                continue
            seen.add(key)

            line_text = output[match.start() : match.start() + 200].split("\n")[0]
            message = line_text[:200] if line_text else ""

            results.append(
                ParsedError(
                    file=file_path,
                    line=line,
                    column=column,
                    message=message,
                )
            )
    return results
