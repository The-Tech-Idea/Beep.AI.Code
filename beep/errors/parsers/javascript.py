"""JavaScript / Node.js error parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_NODE_ERROR_RE = re.compile(
    r"(SyntaxError|ReferenceError|TypeError|RangeError|URIError|EvalError|"
    r"AssertionError|AggregateError):?\s*(.*)"
)

_NODE_LOC_RE = re.compile(
    r"at\s+"
    r"(?:[^\s]+\s+)?"
    r"(?:"
    r"\((?P<file_paren>[^):]+):(?P<line_paren>\d+):(?P<col_paren>\d+)\)"
    r"|"
    r"(?P<file_bare>[^:]+):(?P<line_bare>\d+):(?P<col_bare>\d+)"
    r")"
)

_NPM_ERROR_RE = re.compile(r"npm\s+(?:ERR!|error)\s+(.*)")


def parse_javascript_errors(output: str) -> list[ParsedError]:
    errors: list[ParsedError] = []
    lines = output.splitlines()
    seen_locations: set[tuple[str, int, int]] = set()

    for i, line in enumerate(lines):
        loc_match = _NODE_LOC_RE.search(line)
        if loc_match:
            file_path = loc_match.group("file_paren") or loc_match.group("file_bare") or ""
            err_line = int(loc_match.group("line_paren") or loc_match.group("line_bare") or "0")
            err_col = int(loc_match.group("col_paren") or loc_match.group("col_bare") or "0")

            loc_key = (file_path, err_line, err_col)
            if loc_key in seen_locations:
                continue
            seen_locations.add(loc_key)

            msg = ""
            code: str | None = None
            for j in range(max(0, i - 3), min(i + 2, len(lines))):
                err_match = _NODE_ERROR_RE.search(lines[j])
                if err_match:
                    code = err_match.group(1)
                    detail = err_match.group(2).strip() if err_match.group(2) else ""
                    msg = f"{code}: {detail}".strip() if detail else code
                    break

            errors.append(
                ParsedError(
                    file=file_path,
                    line=err_line,
                    column=err_col,
                    code=code,
                    message=msg,
                )
            )
            continue

        npm_match = _NPM_ERROR_RE.search(line)
        if npm_match:
            detail = npm_match.group(1).strip()
            if detail:
                errors.append(
                    ParsedError(
                        code="NPM",
                        message=f"npm error: {detail}",
                    )
                )

    return errors


def describe_js_error(code: str) -> str | None:
    common = {
        "SyntaxError": "Invalid JavaScript syntax — check for missing brackets, semicolons, or keywords.",
        "ReferenceError": "Variable or function is not defined in the current scope.",
        "TypeError": "Value is not of the expected type — check method calls on wrong object types.",
        "RangeError": "Value is outside the allowed range — check array indices or recursion depth.",
        "URIError": "Invalid URI — check encode/decode URI calls.",
        "AssertionError": "Assertion failed — check the condition being tested.",
    }
    return common.get(code)
