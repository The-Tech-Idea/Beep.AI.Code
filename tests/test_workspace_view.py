"""Tests for shared workspace file and tree viewing helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from beep.workspace.view import read_workspace_file, show_workspace_tree


def test_read_workspace_file_returns_content() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "sample.txt"
        target.write_text("alpha\nbeta\n", encoding="utf-8")

        content = read_workspace_file(
            target,
            start_line=2,
            show_numbers=False,
            highlight=False,
        )

    assert content == "beta"


def test_read_workspace_file_wraps_read_exception() -> None:
    target = Path.cwd() / "AGENTS.md"

    with patch("beep.workspace.view.read_file", side_effect=PermissionError("denied")):
        with pytest.raises(RuntimeError, match="Failed to read file: denied"):
            read_workspace_file(target)


def test_show_workspace_tree_requires_directory() -> None:
    with pytest.raises(ValueError, match="Not a directory"):
        show_workspace_tree("missing-directory")


def test_show_workspace_tree_delegates_to_display_tree() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        with patch("beep.workspace.view.display_tree") as display_mock:
            show_workspace_tree(root, max_depth=5, show_all=True)

    display_mock.assert_called_once_with(root.resolve(), max_depth=5, show_all=True)