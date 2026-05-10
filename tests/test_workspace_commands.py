"""Tests for workspace command error handling."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.exceptions import Exit

from beep.commands.workspace import cat_cmd, grep_cmd, tree_cmd


def test_cat_cmd_handles_read_file_exception(capsys) -> None:
    target = Path.cwd() / "AGENTS.md"
    with patch(
        "beep.commands.workspace.read_workspace_file",
        side_effect=RuntimeError("Failed to read file: denied"),
    ):
        with pytest.raises(Exit):
            cat_cmd(path=str(target))
    out = capsys.readouterr().out
    assert "failed to read file" in out.lower()


def test_tree_cmd_handles_display_exception(capsys) -> None:
    with patch(
        "beep.commands.workspace.show_workspace_tree",
        side_effect=RuntimeError("Failed to display tree: boom"),
    ):
        with pytest.raises(Exit):
            tree_cmd(path=".")
    out = capsys.readouterr().out
    assert "failed to display tree" in out.lower()


def test_grep_cmd_finds_workspace_match(capsys) -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "sample.py"
        target.write_text("needle\n", encoding="utf-8")

        grep_cmd(pattern="needle", path=td)

    out = capsys.readouterr().out
    assert "sample.py" in out
    assert "needle" in out


def test_grep_cmd_handles_invalid_regex(capsys) -> None:
    with pytest.raises(Exit):
        grep_cmd(pattern="[unclosed", path=".")

    out = capsys.readouterr().out
    assert "invalid regex" in out.lower()
