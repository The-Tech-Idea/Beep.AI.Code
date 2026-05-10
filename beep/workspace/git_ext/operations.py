"""Extended Git operations for agent workflows.

Provides:
- Auto-commit with meaningful messages
- Branch management (create, switch, list)
- Diff analysis
- PR-ready change summaries
"""

from __future__ import annotations

import subprocess
from pathlib import Path




from beep.utils.console import get_console
def run_git(args: list[str], cwd: Path) -> tuple[bool, str, str]:
    """Run a git command.

    Returns:
        (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, "", str(e)


def get_current_branch(workspace_root: Path) -> str | None:
    """Get current git branch name."""
    success, out, _ = run_git(["branch", "--show-current"], workspace_root)
    return out if success else None


def list_branches(workspace_root: Path, remote: bool = False) -> list[str]:
    """List git branches."""
    args = ["branch"]
    if remote:
        args.append("-r")
    success, out, _ = run_git(args, workspace_root)
    if not success:
        return []
    return [b.strip().lstrip("* ") for b in out.splitlines() if b.strip()]


def create_branch(workspace_root: Path, name: str, from_branch: str | None = None) -> bool:
    """Create a new branch."""
    args = ["branch", name]
    if from_branch:
        args.append(from_branch)
    success, _, stderr = run_git(args, workspace_root)
    if not success:
        get_console().print(f"[red]Failed to create branch: {stderr}[/red]")
    return success


def switch_branch(workspace_root: Path, name: str) -> bool:
    """Switch to a branch."""
    success, _, stderr = run_git(["checkout", name], workspace_root)
    if not success:
        get_console().print(f"[red]Failed to switch branch: {stderr}[/red]")
    return success


def get_unstaged_files(workspace_root: Path) -> list[str]:
    """Get list of unstaged files."""
    success, out, _ = run_git(["diff", "--name-only"], workspace_root)
    if not success:
        return []
    return [f for f in out.splitlines() if f]


def get_staged_files(workspace_root: Path) -> list[str]:
    """Get list of staged files."""
    success, out, _ = run_git(["diff", "--cached", "--name-only"], workspace_root)
    if not success:
        return []
    return [f for f in out.splitlines() if f]


def stage_files(workspace_root: Path, files: list[str]) -> bool:
    """Stage files for commit."""
    if not files:
        return True
    success, _, stderr = run_git(["add"] + files, workspace_root)
    if not success:
        get_console().print(f"[red]Failed to stage: {stderr}[/red]")
    return success


def stage_all(workspace_root: Path) -> bool:
    """Stage all changes."""
    success, _, stderr = run_git(["add", "-A"], workspace_root)
    if not success:
        get_console().print(f"[red]Failed to stage all: {stderr}[/red]")
    return success


def commit(workspace_root: Path, message: str, amend: bool = False) -> bool:
    """Create a commit."""
    args = ["commit", "-m", message]
    if amend:
        args.append("--amend")
    success, _, stderr = run_git(args, workspace_root)
    if not success:
        get_console().print(f"[red]Commit failed: {stderr}[/red]")
    return success


def get_diff_summary(workspace_root: Path) -> str:
    """Get a summary of all changes."""
    lines = []

    success, out, _ = run_git(["diff", "--stat"], workspace_root)
    if success and out:
        lines.append("Unstaged changes:")
        lines.append(out)

    success, out, _ = run_git(["diff", "--cached", "--stat"], workspace_root)
    if success and out:
        lines.append("Staged changes:")
        lines.append(out)

    return "\n\n".join(lines) if lines else "No changes"


def generate_commit_message(
    workspace_root: Path,
    goal: str,
    max_length: int = 72,
) -> str:
    """Generate a conventional commit message from a goal.

    Uses conventional commits format: type: description
    """
    changed = get_unstaged_files(workspace_root)
    if not changed:
        changed = get_staged_files(workspace_root)

    file_types = set()
    for f in changed:
        ext = Path(f).suffix.lower()
        if ext in (".py",):
            file_types.add("python")
        elif ext in (".js", ".ts", ".tsx", ".jsx"):
            file_types.add("javascript")
        elif ext in (".md",):
            file_types.add("docs")
        elif ext in (".css", ".scss", ".html"):
            file_types.add("style")
        elif ext in (".json", ".yaml", ".yml", ".toml"):
            file_types.add("config")

    if "docs" in file_types and len(file_types) == 1:
        prefix = "docs"
    elif "config" in file_types and len(file_types) == 1:
        prefix = "chore"
    elif any(t in file_types for t in ("python", "javascript")):
        keywords = ("add", "create", "new", "implement")
        prefix = "feat" if any(w in goal.lower() for w in keywords) else "fix"
    else:
        prefix = "feat"

    description = goal.strip()[:max_length - len(prefix) - 2]
    return f"{prefix}: {description}"
