"""Tests for git worktree manager and parallel coordinator."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from beep.agent.parallel.worktrees import WorktreeManager
from beep.agent.parallel.coordinator import (
    CoordinatedResult,
    FanOutResult,
    ParallelCoordinator,
)


class TestWorktreeManager:
    def test_create_calls_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            manager = WorktreeManager(root)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""
                mock_run.return_value.stderr = ""
                mock_run.return_value.returncode = 0

                run_id, worktree = manager.create("test-1")
                assert run_id == "test-1"
                assert ".beep-worktree-test-1" in str(worktree)

    def test_cleanup_calls_git_worktree_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            manager = WorktreeManager(root)
            manager._active["test-1"] = Path(tmp) / ".beep-worktree-test-1"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""
                mock_run.return_value.stderr = ""
                mock_run.return_value.returncode = 0

                manager.cleanup("test-1")
                assert "test-1" not in manager._active

    def test_cleanup_nonexistent_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            manager = WorktreeManager(root)
            manager.cleanup("nonexistent")

    def test_list_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            manager = WorktreeManager(root)
            manager._active["a"] = Path(tmp)
            manager._active["b"] = Path(tmp)
            active = manager.list_active()
            assert len(active) == 2
            assert "a" in active
            assert "b" in active

    def test_cleanup_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            manager = WorktreeManager(root)
            manager._active["a"] = Path(tmp)
            manager._active["b"] = Path(tmp)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""
                mock_run.return_value.stderr = ""
                mock_run.return_value.returncode = 0
                manager.cleanup_all()
                assert len(manager._active) == 0


class TestCoordinatedResult:
    def test_defaults(self) -> None:
        r = CoordinatedResult(run_id="r1", goal="test", success=True)
        assert r.summary == ""
        assert r.error == ""

    def test_with_summary(self) -> None:
        r = CoordinatedResult(run_id="r1", goal="test", success=True, summary="done")
        assert r.summary == "done"


class TestFanOutResult:
    def test_success_count(self) -> None:
        r = FanOutResult(
            results=[
                CoordinatedResult(run_id="a", goal="x", success=True),
                CoordinatedResult(run_id="b", goal="x", success=False),
                CoordinatedResult(run_id="c", goal="x", success=True),
            ]
        )
        assert r.success_count == 2

    def test_empty(self) -> None:
        r = FanOutResult()
        assert r.success_count == 0
        assert r.results == []
        assert r.combined_summary == ""
