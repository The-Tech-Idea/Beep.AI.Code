"""Tests for shared workspace edit preparation."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from beep.workspace.editing import prepare_workspace_edit


def test_prepare_workspace_edit_loads_existing_content() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "sample.txt"
        target.write_text("before", encoding="utf-8")

        prepared = prepare_workspace_edit(target, new_content="after")

    assert prepared.path == target
    assert prepared.old_content == "before"
    assert prepared.new_content == "after"
    assert prepared.to_undo_record() == {
        "path": target,
        "old": "before",
        "new": "after",
    }


def test_prepare_workspace_edit_uses_empty_content_for_missing_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "new.txt"

        prepared = prepare_workspace_edit(target, new_content="after")

    assert prepared.old_content == ""


def test_prepare_workspace_edit_wraps_read_error() -> None:
    target = Path.cwd() / "AGENTS.md"

    with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
        with pytest.raises(RuntimeError, match="Error: denied"):
            prepare_workspace_edit(target, new_content="after")