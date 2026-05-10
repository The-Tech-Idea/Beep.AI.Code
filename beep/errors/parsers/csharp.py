"""C# / .NET error parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_CSHARP_ERROR_RE = re.compile(
    r"(?P<file>.+\.cs)\((?P<line>\d+),(?P<column>\d+)\):\s*"
    r"(?P<severity>error|warning)\s+(?P<code>CS\d+):\s*(?P<message>.+)"
)

_CS_KNOWN_CODES: dict[str, str] = {
    "CS0103": "The name does not exist in the current context.",
    "CS0246": "The type or namespace name could not be found. Missing using directive or assembly reference?",
    "CS1002": "Expected ';'.",
    "CS1061": "Type does not contain a definition for this member.",
    "CS0117": "Type does not contain a definition for this member.",
    "CS0029": "Cannot implicitly convert type.",
    "CS0168": "Variable is declared but never used.",
    "CS0234": "The type or namespace does not exist in the namespace.",
    "CS0535": "Class does not implement interface member.",
    "CS1503": "Argument type mismatch -- cannot convert argument.",
}


def parse_csharp_errors(output: str) -> list[ParsedError]:
    errors: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()
    for line in output.splitlines():
        match = _CSHARP_ERROR_RE.search(line)
        if match:
            key = (match.group("file"), int(match.group("line")))
            if key not in seen:
                seen.add(key)
                errors.append(
                    ParsedError(
                        file=match.group("file"),
                        line=int(match.group("line")),
                        column=int(match.group("column")),
                        code=match.group("code"),
                        message=f"{match.group('severity')}: {match.group('message')}",
                    )
                )
    return errors


def describe_cs_error(code: str) -> str | None:
    return _CS_KNOWN_CODES.get(code)
