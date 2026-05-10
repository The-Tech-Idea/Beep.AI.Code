"""Git operations for workspace integration."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path




from beep.utils.console import get_console
@dataclass
class CommitInfo:
    """Basic commit metadata."""

    hash: str
    message: str
    author: str
    date: str


def _run_git(args: list[str], cwd: Path) -> str | None:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_git_status(workspace_root: Path) -> str | None:
    """Get git status output."""
    return _run_git(["status", "--short"], workspace_root)


def get_git_diff(workspace_root: Path, staged: bool = False) -> str | None:
    """Get git diff."""
    if not is_git_repo(workspace_root):
        return None
    args = ["diff"]
    if staged:
        args = ["diff", "--staged"]
    return _run_git(args, workspace_root)


def get_git_diff_for_file(workspace_root: Path, file_path: str) -> str | None:
    """Get diff for a specific file."""
    if not is_git_repo(workspace_root):
        return None
    return _run_git(["diff", "--", file_path], workspace_root)


def get_git_log(workspace_root: Path, max_commits: int = 10) -> str | None:
    """Get recent git log."""
    return _run_git(
        ["log", f"-{max_commits}", "--oneline", "--decorate"],
        workspace_root,
    )


def get_git_blame(workspace_root: Path, file_path: str) -> str | None:
    """Get git blame for a file."""
    return _run_git(["blame", file_path], workspace_root)


def is_git_repo(workspace_root: Path) -> bool:
    """Check if directory is a git repository."""
    return (workspace_root / ".git").exists()


def get_recent_commits(workspace_root: Path, n: int = 5) -> list[CommitInfo]:
    """Get recent commits as structured data.

    Returns a list of CommitInfo for the most recent n commits.
    Returns an empty list if not a git repo or git is unavailable.
    """
    if not is_git_repo(workspace_root):
        return []
    fmt = "%H\x1f%s\x1f%an\x1f%ai"
    raw = _run_git(["log", f"-{n}", f"--format={fmt}"], workspace_root)
    if not raw:
        return []
    commits = []
    for line in raw.splitlines():
        parts = line.split("\x1f", 3)
        if len(parts) == 4:
            commits.append(CommitInfo(hash=parts[0], message=parts[1], author=parts[2], date=parts[3]))
    return commits
