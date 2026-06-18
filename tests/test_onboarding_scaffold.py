"""Tests for project scaffold and beep init command."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from beep.onboarding.scaffold import ProjectScaffold


class TestProjectScaffold:
    def test_scaffold_creates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            scaffold = ProjectScaffold(root)
            result = scaffold.scaffold()
            assert len(result.created) == 4
            assert (root / ".beep.md").exists()
            assert (root / ".beep" / "rules.md").exists()
            assert (root / ".beep" / "ignore").exists()
            assert (root / ".beep" / "commands.md").exists()

    def test_scaffold_skips_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            scaffold = ProjectScaffold(root)
            result = scaffold.scaffold()
            assert len(result.created) == 4
            result2 = scaffold.scaffold()
            assert len(result2.created) == 0
            assert len(result2.skipped) == 4

    def test_scaffold_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            scaffold = ProjectScaffold(root)
            scaffold.scaffold()
            result = scaffold.scaffold(force=True)
            assert len(result.created) == 4

    def test_memory_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            scaffold = ProjectScaffold(root)
            scaffold.scaffold()
            content = (root / ".beep.md").read_text()
            assert "Project Memory" in content
            assert "Tech stack" in content

    def test_rules_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            scaffold = ProjectScaffold(root)
            scaffold.scaffold()
            content = (root / ".beep" / "rules.md").read_text()
            assert "Project Rules" in content
            assert "Code Standards" in content

    def test_ignore_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            scaffold = ProjectScaffold(root)
            scaffold.scaffold()
            content = (root / ".beep" / "ignore").read_text()
            assert "node_modules" in content
            assert ".git/" in content


class TestInitCommand:
    def test_init_creates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            with patch("beep.commands.init.find_workspace_root", return_value=root):
                from beep.commands.init import init_cmd

                init_cmd()
            assert (root / ".beep.md").exists()
            assert (root / ".beep" / "rules.md").exists()

    def test_init_rerun_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproject"
            root.mkdir()
            with patch("beep.commands.init.find_workspace_root", return_value=root):
                from beep.commands.init import init_cmd

                init_cmd()
                init_cmd()
            assert (root / ".beep.md").exists()
