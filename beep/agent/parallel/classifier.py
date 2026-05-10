"""Tool classification for parallel execution.

Read-only tools can run concurrently. Write tools must run sequentially
to avoid race conditions and filesystem conflicts.
"""

from __future__ import annotations

_READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        "file_read",
        "search",
        "glob_files",
        "list_directory",
        "context",
        "code_snippet_list",
        "project_validate",
    }
)

_WRITE_TOOLS: frozenset[str] = frozenset(
    {
        "file_write",
        "file_edit",
        "single_edit",
        "shell",
        "git",
        "project_scaffold",
        "code_snippet",
        "todo_write",
        "dispatch_agent",
    }
)


def is_read_only_tool(tool_name: str) -> bool:
    """Check if a tool is safe to run in parallel.

    Read-only tools don't modify the workspace and can be
    executed concurrently without conflicts.
    """
    return tool_name in _READ_ONLY_TOOLS
