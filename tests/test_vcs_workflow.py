"""Tests for GitWorkflow and git CLI commands."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from beep.vcs.workflow import GitWorkflow, GitWorkflowError


def _init_temp_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, capture_output=True)
    return root


class TestGitWorkflow:
    def test_ensure_repo_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            wf = GitWorkflow(root)
            wf.ensure_repo()

    def test_ensure_repo_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wf = GitWorkflow(Path(tmp))
            with pytest.raises(GitWorkflowError, match="Not a git repo"):
                wf.ensure_repo()

    def test_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            wf = GitWorkflow(root)
            status = wf.status()
            assert isinstance(status, str)

    def test_diff_no_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            wf = GitWorkflow(root)
            diff = wf.diff()
            assert diff == ""

    def test_diff_with_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            (root / "test.txt").write_text("hello")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)
            (root / "test.txt").write_text("world")
            wf = GitWorkflow(root)
            diff = wf.diff()
            assert "world" in diff

    def test_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            (root / "test.txt").write_text("hello")
            wf = GitWorkflow(root)
            assert wf.commit("add file", all_changes=True)
            diff = wf.diff()
            assert diff == ""

    def test_branch_create_and_switch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            (root / "test.txt").write_text("hello")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

            wf = GitWorkflow(root)
            assert wf.branch("feature-x")
            import beep.workspace.git_ext.operations as ops

            branch = ops.get_current_branch(root)
            assert branch == "feature-x"

    def test_pull_request_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            (root / "test.txt").write_text("hello")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

            wf = GitWorkflow(root)
            info = wf.pull_request_info()
            assert "branch" in info
            assert "diff" in info


class TestGitCommands:
    def test_commit_cmd_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            (root / "test.txt").write_text("hello")
            with patch("beep.commands.git.find_workspace_root", return_value=root):
                from beep.commands.git import git_commit_cmd

                git_commit_cmd(message="test", all=True)
                result = subprocess.run(
                    ["git", "log", "--oneline"], cwd=root, capture_output=True, text=True
                )
                assert "test" in result.stdout

    def test_diff_cmd_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            (root / "test.txt").write_text("hello")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)
            (root / "test.txt").write_text("world")
            with patch("beep.commands.git.find_workspace_root", return_value=root):
                from beep.commands.git import git_diff_cmd

                git_diff_cmd(staged=False, file=None)  # type: ignore[call-arg]

    def test_status_cmd_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_temp_repo(Path(tmp))
            with patch("beep.commands.git.find_workspace_root", return_value=root):
                from beep.commands.git import git_status_cmd

                git_status_cmd()
