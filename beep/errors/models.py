"""Structured error models for agent tool failures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ErrorCategory(str, Enum):
    """Known error categories for structured tool errors."""

    BUILD_ERROR = "BuildError"
    TEST_FAILURE = "TestFailure"
    COMMAND_TIMEOUT = "CommandTimeout"
    PERMISSION_DENIED = "PermissionDenied"
    FILE_NOT_FOUND = "FileNotFound"
    INVALID_PATCH = "InvalidPatch"
    MCP_TOOL_ERROR = "McpToolError"
    MISSING_DEPENDENCY = "MissingDependency"
    SYNTAX_ERROR = "SyntaxError"
    RUNTIME_ERROR = "RuntimeError"
    UNKNOWN_TOOL = "UnknownTool"
    REPEATED_FAILURE = "RepeatedFailure"
    INVALID_ARGUMENTS = "InvalidArguments"
    POLICY_VIOLATION = "PolicyViolation"
    UNKNOWN = "Unknown"


@dataclass
class StructuredToolError:
    """Normalized error representation for agent self-correction."""

    tool_name: str
    error_type: ErrorCategory
    message: str
    command: str | None = None
    file_path: str | None = None
    line: int | None = None
    column: int | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    retryable: bool = True
    suggested_action: str | None = None

    def to_xml(self) -> str:
        """Render as XML for injection into the agent prompt."""
        parts: list[str] = ["<tool_error>"]
        parts.append(f"  <tool>{self.tool_name}</tool>")
        parts.append(f"  <error_type>{self.error_type.value}</error_type>")
        parts.append(f"  <message>{self.message}</message>")
        if self.command:
            parts.append(f"  <command>{self.command}</command>")
        if self.file_path:
            parts.append(f"  <file_path>{self.file_path}</file_path>")
        if self.line is not None:
            parts.append(f"  <line>{self.line}</line>")
        if self.column is not None:
            parts.append(f"  <column>{self.column}</column>")
        if self.exit_code is not None:
            parts.append(f"  <exit_code>{self.exit_code}</exit_code>")
        if self.stderr:
            parts.append(f"  <stderr>{_truncate(self.stderr, 2000)}</stderr>")
        if self.stdout:
            parts.append(f"  <stdout>{_truncate(self.stdout, 1000)}</stdout>")
        parts.append(f"  <retryable>{str(self.retryable).lower()}</retryable>")
        if self.suggested_action:
            parts.append(f"  <suggested_action>{self.suggested_action}</suggested_action>")
        parts.append("</tool_error>")
        return "\n".join(parts)

    def to_prompt_section(self) -> str:
        """Render as a readable section for the system prompt."""
        lines: list[str] = [
            f"ERROR in tool '{self.tool_name}':",
            f"  Type: {self.error_type.value}",
            f"  Message: {self.message}",
        ]
        if self.command:
            lines.append(f"  Command: {self.command}")
        if self.file_path:
            loc = self.file_path
            if self.line is not None:
                loc += f":{self.line}"
                if self.column is not None:
                    loc += f":{self.column}"
            lines.append(f"  Location: {loc}")
        if self.exit_code is not None:
            lines.append(f"  Exit code: {self.exit_code}")
        if self.stderr:
            lines.append(f"  Stderr: {_truncate(self.stderr, 1000)}")
        if self.suggested_action:
            lines.append(f"  Suggested action: {self.suggested_action}")
        if not self.retryable:
            lines.append("  This error is NOT retryable — change your approach.")
        return "\n".join(lines)


@dataclass
class ErrorHistory:
    """Track errors across an agent run for pattern detection."""

    errors: list[StructuredToolError] = field(default_factory=list)
    failure_counts: dict[str, int] = field(default_factory=dict)

    def add(self, error: StructuredToolError) -> None:
        self.errors.append(error)
        key = f"{error.tool_name}:{error.error_type.value}"
        self.failure_counts[key] = self.failure_counts.get(key, 0) + 1

    def is_repeated(self, error: StructuredToolError, threshold: int = 2) -> bool:
        key = f"{error.tool_name}:{error.error_type.value}"
        return self.failure_counts.get(key, 0) >= threshold

    def clear(self) -> None:
        self.errors.clear()
        self.failure_counts.clear()


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... ({len(text) - max_len} chars truncated)"
