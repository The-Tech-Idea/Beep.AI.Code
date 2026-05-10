"""Language-specific error parsers for structured error extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedError:
    file: str | None = None
    line: int | None = None
    column: int | None = None
    code: str | None = None
    message: str = ""


def extract_location(
    match: re.Match[str],
    output: str,
    file_group: int = 1,
    line_group: int = 2,
    column_group: int = 3,
    message_group: int = 4,
) -> ParsedError:
    """Extract a ParsedError from a regex match with standard group indices."""
    groups = match.groups()

    file_path = groups[file_group - 1] if len(groups) > file_group - 1 else None
    line_str = groups[line_group - 1] if len(groups) > line_group - 1 else None
    column_str = groups[column_group - 1] if len(groups) > column_group - 1 else None

    try:
        line = int(line_str) if line_str else None
    except ValueError:
        line = None
    try:
        column = int(column_str) if column_str else None
    except ValueError:
        column = None

    message = ""
    if len(groups) > message_group - 1 and groups[message_group - 1]:
        message = str(groups[message_group - 1])[:200]
    if not message:
        line_text = output[match.start() : match.start() + 200].split("\n")[0]
        message = line_text[:200]

    return ParsedError(
        file=file_path,
        line=line,
        column=column,
        message=message,
    )
