"""Human approval gate for destructive operations."""

from __future__ import annotations

from rich.prompt import Confirm


from beep.utils.console import get_console
DESTRUCTIVE_TOOLS = {"file_write", "file_edit", "single_edit", "shell", "python_rename"}

# git subcommands that mutate the repository; read-only subcommands never
# require approval even though they go through the same `git` tool.
_GIT_WRITE_SUBCOMMANDS = {"add", "commit", "stash", "restore", "reset"}


def requires_approval(tool_name: str, arguments: dict | None = None) -> bool:
    """Check if a tool call requires human approval.

    For the ``git`` tool the decision is argument-aware: only write
    subcommands (add, commit, stash, restore, reset) require approval;
    read-only ones (status, diff, log, show) never do.
    """
    if tool_name == "git":
        if arguments:
            subcommand = arguments.get("subcommand", "").strip().split()[0].lower()
            return subcommand in _GIT_WRITE_SUBCOMMANDS
        # Unknown args — be conservative.
        return True
    return tool_name in DESTRUCTIVE_TOOLS


def request_approval(tool_name: str, arguments: dict) -> bool:
    """Request human approval for a tool execution.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments

    Returns:
        True if approved
    """
    get_console().print(f"\n[yellow]Tool requires approval: {tool_name}[/yellow]")
    get_console().print(f"Arguments: {arguments}")

    return Confirm.ask("Approve?", default=False)
