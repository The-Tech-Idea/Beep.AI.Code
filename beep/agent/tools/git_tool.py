"""Git tool for agent — safe, allowlisted git operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.workspace.git import (
    get_git_diff,
    get_git_diff_for_file,
    get_git_log,
    get_git_status,
    is_git_repo,
)

# Read-only subcommands that never modify the repository.
_READ_SUBCOMMANDS = {"status", "diff", "log", "show"}

# Write subcommands that require human approval (added to DESTRUCTIVE_TOOLS).
_WRITE_SUBCOMMANDS = {"add", "commit", "stash", "restore", "reset"}

_ALLOWED_SUBCOMMANDS = _READ_SUBCOMMANDS | _WRITE_SUBCOMMANDS

_MAX_OUTPUT = 8_000


def _trim(text: str) -> str:
    if len(text) <= _MAX_OUTPUT:
        return text
    return text[:_MAX_OUTPUT] + f"\n[... output truncated at {_MAX_OUTPUT} chars]"


class GitTool(BaseTool):
    """Run safe git commands against the workspace repository.

    Supported subcommands
    ---------------------
    Read-only (never need approval):
      status                    → working tree status
      diff                      → unstaged changes (all files)
      diff <file>               → unstaged changes for one file
      diff --staged             → staged changes
      log                       → recent commits (last 10)
      log -n <N>                → last N commits
      show <ref>                → show a commit or object

    Write (require approval when auto_approve is off):
      add <file|.>              → stage files
      commit -m <message>       → commit staged changes
      stash                     → stash working tree changes
      stash pop                 → restore last stash
      restore <file>            → discard changes to a file
      reset HEAD <file>         → unstage a file

    Any subcommand not in this list is rejected.
    """

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root.resolve() if workspace_root else None

    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return (
            "Run git commands in the workspace repository. "
            "Pass the full command as 'subcommand', e.g. subcommand='status', "
            "subcommand='diff src/main.py', subcommand='log -n 5', "
            "subcommand='commit -m fix: typo'. "
            "Only an allowlisted set of safe subcommands is permitted."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "subcommand": {
                "type": "string",
                "description": (
                    "The git subcommand and its arguments as a single string. "
                    "Examples: 'status', 'diff', 'diff src/app.py', "
                    "'log -n 5', 'add .', 'commit -m fix: correct typo', "
                    "'stash', 'stash pop', 'restore src/app.py'."
                ),
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return []

    async def execute(self, **kwargs: Any) -> ToolResult:
        subcommand_str: str = kwargs.get("subcommand", "").strip()
        if not subcommand_str:
            return ToolResult(success=False, output="", error="subcommand is required")

        root = self._workspace_root or Path.cwd()

        if not is_git_repo(root):
            return ToolResult(
                success=False,
                output="",
                error="Not a git repository (no .git found in workspace)",
            )

        parts = subcommand_str.split()
        verb = parts[0].lower()

        if verb not in _ALLOWED_SUBCOMMANDS:
            return ToolResult(
                success=False,
                output="",
                error=(
                    f"Subcommand '{verb}' is not allowed. "
                    f"Permitted: {', '.join(sorted(_ALLOWED_SUBCOMMANDS))}"
                ),
            )

        # Route to workspace/git.py helpers for common read paths;
        # fall back to a direct subprocess call for everything else.
        output: str | None = None

        if verb == "status" and len(parts) == 1:
            output = get_git_status(root)

        elif verb == "diff":
            rest = parts[1:]
            if not rest:
                output = get_git_diff(root, staged=False)
            elif rest == ["--staged"]:
                output = get_git_diff(root, staged=True)
            elif len(rest) == 1 and not rest[0].startswith("-"):
                output = get_git_diff_for_file(root, rest[0])
            else:
                output = _raw_git(parts, root)

        elif verb == "log":
            rest = parts[1:]
            if not rest:
                output = get_git_log(root, max_commits=10)
            elif len(rest) == 2 and rest[0] == "-n" and rest[1].isdigit():
                output = get_git_log(root, max_commits=int(rest[1]))
            else:
                output = _raw_git(parts, root)

        else:
            output = _raw_git(parts, root)

        if output is None:
            return ToolResult(success=False, output="", error=f"git {subcommand_str} failed")

        return ToolResult(success=True, output=_trim(output) if output else "(no output)")


def _raw_git(args: list[str], cwd: Path) -> str | None:
    """Run an arbitrary allowlisted git command and return stdout."""
    import subprocess

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "(no output)"
        # Non-zero exit: surface stderr so the agent can self-correct.
        msg = result.stderr.strip() or result.stdout.strip()
        return None if not msg else f"[exit {result.returncode}] {msg}"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
