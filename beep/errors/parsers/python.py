"""Python error parser."""

from __future__ import annotations

import re

from beep.errors.parsers import ParsedError

_PYTHON_LOC_RE = re.compile(r'File\s+"([^"]+)"\s*,?\s*line\s+(\d+)(?:\s*,?\s*col(?:umn)?\s*(\d+))?')
_PYTHON_ERR_RE = re.compile(
    r"(ModuleNotFoundError|ImportError|NameError|TypeError|ValueError|AttributeError|"
    r"SyntaxError|IndentationError|AssertionError|KeyError|IndexError|RuntimeError"
    r"|OSError|UnicodeError|ZeroDivisionError):?\s*(.*)"
)


def parse_python_errors(output: str) -> list[ParsedError]:
    errors: list[ParsedError] = []
    seen: set[tuple[str | None, int | None]] = set()
    lines = output.splitlines()
    i = 0
    while i < len(lines):
        loc_match = _PYTHON_LOC_RE.search(lines[i])
        if loc_match:
            msg = ""
            code: str | None = None
            j = i + 1
            while j < min(i + 4, len(lines)):
                err_match = _PYTHON_ERR_RE.search(lines[j])
                if err_match:
                    exc_type = err_match.group(1)
                    exc_msg = err_match.group(2).strip() if err_match.group(2) else ""
                    code = exc_type
                    msg = f"{exc_type}: {exc_msg}" if exc_msg else exc_type
                    break
                j += 1
            key = (loc_match.group(1), int(loc_match.group(2)))
            if key not in seen:
                seen.add(key)
                errors.append(
                    ParsedError(
                        file=loc_match.group(1),
                        line=int(loc_match.group(2)),
                        column=int(loc_match.group(3)) if loc_match.group(3) else None,
                        code=code,
                        message=msg,
                    )
                )
            i += 1
        else:
            i += 1
    return errors
