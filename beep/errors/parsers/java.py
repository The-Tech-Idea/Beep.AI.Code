"""Java error output parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError, extract_location

_JAVA_ERROR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"([^:\s]+\.(?:java|kt)):(\d+)(?::(\d+))?"), "compile"),
    (re.compile(r"at\s+([\w.$]+)\(([^:\s]+\.java):(\d+)\)"), "stacktrace"),
    (re.compile(r"(?:error|warning):\s*([^:\s]+\.(?:java|kt)):(\d+):(\d+)?"), "compiler"),
]


def parse_java_errors(output: str) -> list[ParsedError]:
    """Extract error locations from Java compiler/test output."""
    results: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()
    for pattern, _ in _JAVA_ERROR_PATTERNS:
        for match in pattern.finditer(output):
            groups = match.groups()
            file_path = groups[0] if len(groups) > 0 else None
            line_str = groups[1] if len(groups) > 1 else None
            column_str = groups[2] if len(groups) > 2 else None

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
