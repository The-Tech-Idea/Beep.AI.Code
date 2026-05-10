"""TypeScript / JavaScript error parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_TSC_ERROR_RE = re.compile(
    r"(?P<file>[^\(]+)\((?P<line>\d+),(?P<column>\d+)\):\s*"
    r"error\s+(?P<code>TS\d+):\s*(?P<message>.+)"
)

_TS_KNOWN_CODES: dict[str, str] = {
    "TS2304": "Cannot find name -- the variable or type is not declared.",
    "TS2307": "Cannot find module -- the import path is wrong or the package is missing.",
    "TS2322": "Type is not assignable -- the assigned value doesn't match the expected type.",
    "TS2339": "Property does not exist on this type.",
    "TS2345": "Argument of type is not assignable to parameter.",
    "TS2531": "Object is possibly null.",
    "TS2532": "Object is possibly undefined.",
    "TS2551": "Property does not exist. Did you mean ...?",
    "TS2769": "No overload matches this call.",
    "TS7006": "Parameter implicitly has an 'any' type.",
}


def parse_typescript_errors(output: str) -> list[ParsedError]:
    errors: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()
    for line in output.splitlines():
        match = _TSC_ERROR_RE.search(line)
        if match:
            key = (match.group("file").strip(), int(match.group("line")))
            if key not in seen:
                seen.add(key)
                errors.append(
                    ParsedError(
                        file=match.group("file").strip(),
                        line=int(match.group("line")),
                        column=int(match.group("column")),
                        code=match.group("code"),
                        message=match.group("message"),
                    )
                )
    return errors


def describe_ts_error(code: str) -> str | None:
    return _TS_KNOWN_CODES.get(code)
