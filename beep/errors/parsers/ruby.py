"""Ruby error output parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_RUBY_ERROR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"([^:\s]+\.rb):(\d+)(?::in\s+[`\']([^\'\']+)\')?"),
    re.compile(r"SyntaxError:\s+([^:\s]+\.rb):(\d+):"),
    re.compile(r"Failure/Error:.*?\n\s+#\s+([^:\s]+\.rb):(\d+)"),
]


def parse_ruby_errors(output: str) -> list[ParsedError]:
    """Extract error locations from Ruby/RSpec test output."""
    results: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()

    for pattern in _RUBY_ERROR_PATTERNS:
        for match in pattern.finditer(output):
            groups = match.groups()
            file_path = groups[0] if len(groups) > 0 and groups[0].endswith(".rb") else None
            line_str = groups[1] if len(groups) > 1 else None

            try:
                line = int(line_str) if line_str else None
            except ValueError:
                continue

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
                    column=None,
                    message=message,
                )
            )
    return results
