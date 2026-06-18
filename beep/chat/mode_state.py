"""Plan/Build agent mode state mapped to sandbox modes.

Provides a user-facing toggle between Plan (read-only analysis) and Build
(workspace-write) modes that maps onto the existing SandboxMode permissions.
"""

from __future__ import annotations

from enum import StrEnum

from beep.permissions.manager import SandboxMode


class AgentMode(StrEnum):
    PLAN = "plan"
    BUILD = "build"


MODE_TO_SANDBOX: dict[AgentMode, SandboxMode] = {
    AgentMode.PLAN: SandboxMode.READ_ONLY,
    AgentMode.BUILD: SandboxMode.WORKSPACE_WRITE,
}

SANDBOX_TO_MODE: dict[SandboxMode, AgentMode] = {
    SandboxMode.READ_ONLY: AgentMode.PLAN,
    SandboxMode.WORKSPACE_WRITE: AgentMode.BUILD,
    SandboxMode.FULL_TRUST: AgentMode.BUILD,
}

BANNER_PLAN = (
    "[bold blue]>>> PLAN MODE <<<[/bold blue] "
    "The agent analyses and answers questions without making edits. "
    "Use [bold]/build[/bold] to switch back to edit mode."
)

BANNER_BUILD = (
    "[bold green]>>> BUILD MODE <<<[/bold green] "
    "The agent can read and write files on your behalf. "
    "Use [bold]/plan[/bold] to switch to read-only analysis mode."
)

READ_ONLY_TOOLS = frozenset(
    {
        "file_read",
        "search",
        "list_directory",
        "code_snippet_list",
        "code_snippet_read",
        "code_symbol_search",
        "code_diagnostics",
        "code_hover",
        "code_definition",
        "code_references",
        "semantic_search",
        "find_related_code",
        "todo_write",
        "task",
        "dispatch_agent",
    }
)

WRITE_TOOLS = frozenset(
    {
        "file_write",
        "file_edit",
        "single_edit",
        "shell",
        "execute_watch_event",
    }
)


def build_mode_banner(mode: AgentMode) -> str:
    return BANNER_PLAN if mode == AgentMode.PLAN else BANNER_BUILD


def is_write_tool(tool_name: str) -> bool:
    return tool_name in WRITE_TOOLS


def is_read_only_tool(tool_name: str) -> bool:
    return tool_name in READ_ONLY_TOOLS
