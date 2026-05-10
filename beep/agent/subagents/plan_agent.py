"""Plan sub-agent for architecture and implementation planning."""

from __future__ import annotations

PLAN_TOOLS: frozenset[str] = frozenset(
    {
        "file_read",
        "search",
        "glob_files",
        "list_directory",
        "context",
        "todo_write",
    }
)

PLAN_SYSTEM_PROMPT_SUFFIX = """

You are a planning agent. Your job is to READ the codebase and CREATE PLANS.
You CANNOT write files, edit files, or run shell commands.
Focus on understanding the architecture, identifying critical files,
and designing implementation strategies with trade-offs.
Use todo_write to track your planning steps."""
