"""Explore sub-agent for read-only codebase exploration."""

from __future__ import annotations

EXPLORE_TOOLS: frozenset[str] = frozenset(
    {
        "file_read",
        "search",
        "glob_files",
        "list_directory",
        "context",
        "code_snippet_list",
        "todo_write",
    }
)

EXPLORE_SYSTEM_PROMPT_SUFFIX = """

You are an exploration agent. Your job is to READ and ANALYZE the codebase.
You CANNOT write files, edit files, or run shell commands.
Focus on finding relevant files, understanding structure, and identifying key patterns.
Return a concise summary of your findings."""
