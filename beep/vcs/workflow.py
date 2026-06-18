"""Git workflow service — shared logic for chat commands and CLI."""

from __future__ import annotations

from pathlib import Path

from beep.workspace.git import get_git_diff, get_git_status, is_git_repo


class GitWorkflow:
    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    def ensure_repo(self) -> None:
        if not is_git_repo(self._root):
            raise GitWorkflowError("Not a git repository.")

    def status(self) -> str:
        self.ensure_repo()
        return get_git_status(self._root)

    def diff(self, staged: bool = False, file_path: str | None = None) -> str:
        self.ensure_repo()
        if file_path:
            from beep.workspace.git import get_git_diff_for_file

            return get_git_diff_for_file(self._root, file_path)
        return get_git_diff(self._root, staged=staged)

    def commit(self, message: str, *, all_changes: bool = False) -> bool:
        self.ensure_repo()
        from beep.workspace.git_ext.operations import commit, stage_all

        if all_changes:
            stage_all(self._root)
        return commit(self._root, message)

    def branch(self, name: str, base: str | None = None) -> bool:
        self.ensure_repo()
        from beep.workspace.git_ext.operations import create_branch, switch_branch

        if create_branch(self._root, name, from_branch=base):
            switch_branch(self._root, name)
            return True
        return False

    def pull_request_info(self) -> dict[str, str]:
        self.ensure_repo()
        try:
            from beep.workspace.git_ext.operations import get_current_branch
        except ImportError:
            return {"branch": "unknown"}
        branch = get_current_branch(self._root) or "main"
        diff = self.diff()
        commits = self._recent_commits(5)
        return {"branch": branch, "diff": diff, "recent_commits": commits}

    def _recent_commits(self, count: int) -> str:
        import subprocess

        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--oneline"],
                cwd=self._root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return ""


class GitWorkflowError(Exception):
    pass
