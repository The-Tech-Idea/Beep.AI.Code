"""C/C++ error output parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_CCPP_ERROR_PATTERNS: list[tuple[re.Pattern[str], int | None]] = [
    (
        re.compile(
            r"([^:\s]+\.(?:c|cpp|cc|cxx|h|hpp|hh|hxx)):(\d+):(\d+):\s+(error|warning|fatal error|note):\s+(.*)"
        ),
        4,
    ),
    (
        re.compile(
            r"([^:\s]+\.(?:c|cpp|cc|cxx|h|hpp|hh|hxx)):(\d+):\s+(error|warning|fatal error):\s+(.*)"
        ),
        3,
    ),
    (re.compile(r"In file included from\s+([^:\s]+\.(?:c|cpp|h|hpp)):(\d+):"), None),
]


def parse_ccpp_errors(output: str) -> list[ParsedError]:
    """Extract error locations from C/C++ compiler output (gcc/clang)."""
    results: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()

    for pattern, msg_idx in _CCPP_ERROR_PATTERNS:
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
                column = int(column_str) if column_str and column_str.isdigit() else None
            except ValueError:
                column = None

            message = ""
            if msg_idx is not None and len(groups) > msg_idx:
                message = str(groups[msg_idx])[:200]
            if not message:
                line_text = output[match.start() : match.start() + 200].split("\n")[0]
                message = line_text[:200]

            key = (file_path, line)
            if key in seen:
                continue
            seen.add(key)

            results.append(
                ParsedError(
                    file=file_path,
                    line=line,
                    column=column,
                    message=message,
                )
            )
    return results
