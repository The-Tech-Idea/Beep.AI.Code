"""PHP error output parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_PHP_ERROR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:Parse|Fatal|Warning|Notice|Deprecated)\s+error:\s+(.*?)\s+in\s+([^:\s]+\.php)\s+on\s+line\s+(\d+)"
    ),
    re.compile(r"Parse error:\s+syntax error,\s+.*?in\s+([^:\s]+\.php)\s+on\s+line\s+(\d+)"),
    re.compile(r"([^:\s]+\.php)\s+on\s+line\s+(\d+)"),
    re.compile(r"PHPUnit.*?FAILED!.*?\n.*?\n((?:[^:\s]+\.php):(\d+))", re.DOTALL),
    re.compile(r"(?:Failed asserting|AssertionError).*?\n.*?\n([^:\s]+\.php):(\d+)"),
    re.compile(r"^\s+(/[^:\s]+\.php):(\d+)$", re.MULTILINE),
]


def parse_php_errors(output: str) -> list[ParsedError]:
    """Extract error locations from PHP/PHPUnit output."""
    results: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()

    for pattern in _PHP_ERROR_PATTERNS:
        for match in pattern.finditer(output):
            groups = match.groups()
            file_path = None
            line = None

            for g in groups:
                if g and g.endswith(".php"):
                    file_path = g
                elif g and g.isdigit() and 1 <= int(g) <= 99999:
                    line = int(g)

            if file_path is None:
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
