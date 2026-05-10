"""Inject structured errors into agent message history."""

from __future__ import annotations

from typing import Any

from beep.errors.models import StructuredToolError


def format_error_injection(errors: list[StructuredToolError]) -> str:
    """Format a list of structured errors as an XML block for the agent."""
    if not errors:
        return ""
    parts = ["<tool_errors>"]
    parts.append("  The previous tool calls produced errors. Review and fix them.")
    parts.append("")
    for err in errors:
        parts.append(err.to_xml())
        parts.append("")
    parts.append("</tool_errors>")
    return "\n".join(parts)


def inject_errors_into_messages(
    messages: list[dict[str, Any]],
    errors: list[StructuredToolError],
) -> list[dict[str, Any]]:
    """Append a tool-error message to the conversation history."""
    if not errors:
        return messages
    content = format_error_injection(errors)
    if not content:
        return messages
    return [
        *messages,
        {
            "role": "user",
            "content": (
                "Your previous tool calls produced errors. "
                "Review them carefully and try a different approach if needed.\n\n"
                f"{content}"
            ),
        },
    ]


def build_error_tool_message(error: StructuredToolError) -> dict[str, Any]:
    """Build a single tool-result message from a structured error."""
    return {
        "role": "tool",
        "content": error.to_prompt_section(),
        "tool_call_id": "",
    }
