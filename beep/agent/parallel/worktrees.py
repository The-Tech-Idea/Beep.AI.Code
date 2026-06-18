"""Git worktree manager — create and clean up isolated worktrees for parallel agents."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path


class WorktreeManager:
    """Manage git worktrees for isolated parallel agent runs."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()
        self._active: dict[str, Path] = {}

    def create(self, run_id: str | None = None) -> tuple[str, Path]:
        run_id = run_id or str(uuid.uuid4())[:8]
        worktree_path = self._repo_root.parent / f".beep-worktree-{run_id}"

        self._run_git(
            "worktree",
            "add",
            "--detach",
            str(worktree_path),
            cwd=self._repo_root,
        )

        self._active[run_id] = worktree_path
        return run_id, worktree_path

    def cleanup(self, run_id: str) -> None:
        worktree_path = self._active.pop(run_id, None)
        if worktree_path is None:
            return

        self._run_git(
            "worktree",
            "remove",
            "--force",
            str(worktree_path),
            cwd=self._repo_root,
            allow_error=True,
        )

        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)

    def cleanup_all(self) -> None:
        for run_id in list(self._active.keys()):
            self.cleanup(run_id)

    def list_active(self) -> list[str]:
        return list(self._active.keys())

    def _run_git(
        self,
        *args: str,
        cwd: Path,
        allow_error: bool = False,
    ) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0 and not allow_error:
                raise RuntimeError(result.stderr.strip())
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            if not allow_error:
                raise
            return ""
