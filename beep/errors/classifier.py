"""Classify raw tool failures into structured error categories."""

from __future__ import annotations

import re

from beep.errors.models import ErrorCategory, StructuredToolError
from beep.errors.parsers import ParsedError


_IMPORT_PATTERNS: list[tuple[str, ErrorCategory]] = [
    (r"(?:ModuleNotFoundError|ImportError|No module named)", ErrorCategory.MISSING_DEPENDENCY),
    (r"SyntaxError", ErrorCategory.SYNTAX_ERROR),
    (r"(?:Parse error|Fatal error|syntax error, unexpected)", ErrorCategory.SYNTAX_ERROR),
    (r"(?:FileNotFoundError|No such file or directory|ENOENT)", ErrorCategory.FILE_NOT_FOUND),
    (r"(?:PermissionError|Access denied|EACCES)", ErrorCategory.PERMISSION_DENIED),
    (r"(?:Timeout|timed out)", ErrorCategory.COMMAND_TIMEOUT),
    (r"(?:SEARCH.*not found|No matching lines|FAILED to apply)", ErrorCategory.INVALID_PATCH),
    (r"(?:AssertionError|FAILED|test.*failed|ERROR.*test)", ErrorCategory.TEST_FAILURE),
    (
        r"(?:build.*failed|compilation.*error|cannot find symbol|error CS)",
        ErrorCategory.BUILD_ERROR,
    ),
    (r"(?:error:|error\[|cannot find|undefined:|unknown type)", ErrorCategory.BUILD_ERROR),
    (
        r"(?:ReferenceError|Cannot read propert(?:ies|y)|is not defined)",
        ErrorCategory.RUNTIME_ERROR,
    ),
    (r"(?:npm ERR!|npm error|Cannot find module)", ErrorCategory.MISSING_DEPENDENCY),
]


def classify_error(
    tool_name: str,
    error_text: str,
    *,
    command: str | None = None,
    file_path: str | None = None,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
) -> StructuredToolError:
    """Analyze raw error output and return a StructuredToolError."""
    combined = (stderr or "") + "\n" + (error_text or "")
    error_type = _detect_category(combined, command)
    message = _extract_message(combined)
    suggested = _suggest_action(error_type, tool_name, command, file_path)
    retryable = _is_retryable(error_type)

    loc_info = _extract_location_with_parsers(stderr or combined)

    return StructuredToolError(
        tool_name=tool_name,
        error_type=error_type,
        message=message,
        command=command,
        file_path=file_path or loc_info.file_path,
        line=loc_info.line,
        column=loc_info.column,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        retryable=retryable,
        suggested_action=suggested,
    )


class _LocationInfo:
    __slots__ = ("file_path", "line", "column")

    def __init__(self) -> None:
        self.file_path: str | None = None
        self.line: int | None = None
        self.column: int | None = None


def _extract_location_with_parsers(text: str) -> _LocationInfo:
    """Try language-specific parsers first, then fall back to generic regex."""
    for parsed in _try_language_parsers(text):
        if parsed.file:
            loc = _LocationInfo()
            loc.file_path = parsed.file
            loc.line = parsed.line
            loc.column = parsed.column
            return loc
    return _extract_location_generic(text)


def _try_language_parsers(text: str) -> list[ParsedError]:
    """Attempt language-specific error parsing on the output."""
    from beep.errors.parsers.python import parse_python_errors
    from beep.errors.parsers.csharp import parse_csharp_errors
    from beep.errors.parsers.typescript import parse_typescript_errors
    from beep.errors.parsers.javascript import parse_javascript_errors
    from beep.errors.parsers.java import parse_java_errors
    from beep.errors.parsers.go import parse_go_errors
    from beep.errors.parsers.rust import parse_rust_errors
    from beep.errors.parsers.ruby import parse_ruby_errors
    from beep.errors.parsers.ccpp import parse_ccpp_errors
    from beep.errors.parsers.php import parse_php_errors

    parsers = [
        parse_python_errors,
        parse_csharp_errors,
        parse_typescript_errors,
        parse_javascript_errors,
        parse_java_errors,
        parse_go_errors,
        parse_rust_errors,
        parse_ruby_errors,
        parse_ccpp_errors,
        parse_php_errors,
    ]
    for parser in parsers:
        results = parser(text)
        if results:
            return results
    return []


def _extract_location_generic(text: str) -> _LocationInfo:
    loc = _LocationInfo()
    pattern = r'(?:File\s+")?([^\s"]+\.\w+?)"?\s*,?\s*line\s+(\d+)(?:\s*,?\s*col(?:umn)?\s*(\d+))?'
    m = re.search(pattern, text)
    if m:
        loc.file_path = m.group(1)
        loc.line = int(m.group(2))
        loc.column = int(m.group(3)) if m.group(3) else None
        return loc
    pattern2 = r"([^\s:]+\.\w+):(\d+)(?::(\d+))?"
    m2 = re.search(pattern2, text)
    if m2:
        loc.file_path = m2.group(1)
        loc.line = int(m2.group(2))
        loc.column = int(m2.group(3)) if m2.group(3) else None
    return loc


def _detect_category(text: str, command: str | None) -> ErrorCategory:
    for pattern, category in _IMPORT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return category
    if command:
        cmd_lower = command.lower().strip()
        build_cmds = {
            "build",
            "compile",
            "dotnet build",
            "cargo build",
            "npm run build",
            "mvn compile",
            "gradle build",
            "cmake --build",
            "make",
            "go build",
            "tsc",
            "gcc",
            "g++",
            "clang",
            "cl",
        }
        test_cmds = {
            "test",
            "pytest",
            "jest",
            "cargo test",
            "dotnet test",
            "go test",
            "npm test",
            "mvn test",
            "gradle test",
            "rake test",
            "bundle exec rspec",
            "phpunit",
            "ctest",
        }
        cmd_tokens = set(re.split(r"\s+", cmd_lower))
        if cmd_lower in build_cmds or cmd_tokens & {
            "build",
            "compile",
            "make",
            "gcc",
            "g++",
            "clang",
            "cl",
            "tsc",
        }:
            return ErrorCategory.BUILD_ERROR
        if cmd_lower in test_cmds or cmd_tokens & {
            "test",
            "pytest",
            "jest",
            "phpunit",
            "ctest",
            "rspec",
        }:
            return ErrorCategory.TEST_FAILURE
    return ErrorCategory.RUNTIME_ERROR


def _extract_message(text: str) -> str:
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if line and not line.startswith("Traceback") and not line.startswith("  "):
            return line[:300]
    return lines[0][:300] if lines else "Unknown error"


def _suggest_action(
    category: ErrorCategory,
    tool_name: str,
    command: str | None,
    file_path: str | None,
) -> str | None:
    suggestions: dict[ErrorCategory, str] = {
        ErrorCategory.FILE_NOT_FOUND: "Check the file path. The file may have been moved, renamed, or deleted.",
        ErrorCategory.PERMISSION_DENIED: "You do not have permission to access this resource. Check sandbox policy.",
        ErrorCategory.COMMAND_TIMEOUT: "The command took too long. Try a smaller scope or increase timeout.",
        ErrorCategory.INVALID_PATCH: "The SEARCH block did not match. Read the file first to get the exact content.",
        ErrorCategory.MISSING_DEPENDENCY: "Install the missing package or module before continuing.",
        ErrorCategory.SYNTAX_ERROR: "Fix the syntax error in the file before continuing.",
        ErrorCategory.BUILD_ERROR: "Fix the compile errors before continuing.",
        ErrorCategory.TEST_FAILURE: "Review the test output, fix the failing test or the code under test.",
        ErrorCategory.REPEATED_FAILURE: "This keeps failing. Stop and try a completely different approach.",
    }
    return suggestions.get(category)


def _is_retryable(category: ErrorCategory) -> bool:
    non_retryable = {
        ErrorCategory.PERMISSION_DENIED,
        ErrorCategory.UNKNOWN_TOOL,
        ErrorCategory.POLICY_VIOLATION,
        ErrorCategory.REPEATED_FAILURE,
    }
    return category not in non_retryable
