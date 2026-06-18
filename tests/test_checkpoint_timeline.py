"""Tests for edit checkpoint timeline and undo commands."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from beep.chat.checkpoint_timeline import CheckpointTimeline, EditCheckpoint


class TestEditCheckpoint:
    def test_create(self, tmp_path: Path) -> None:
        p = (tmp_path / "test.py").resolve()
        cp = EditCheckpoint(
            file_path=p,
            original_content="x = 1",
            tool_name="edit",
        )
        assert cp.file_path == p
        assert cp.original_content == "x = 1"
        assert cp.tool_name == "edit"


class TestCheckpointTimeline:
    def test_capture_and_pop(self, tmp_path: Path) -> None:
        tl = CheckpointTimeline()
        assert len(tl) == 0

        a = tmp_path / "a.py"
        a.write_text("a")
        tl.capture(a, "content a", "edit")
        assert len(tl) == 1

        b = tmp_path / "b.py"
        b.write_text("b")
        tl.capture(b, "content b", "file_write")
        assert len(tl) == 2

        cp = tl.pop_last()
        assert cp is not None
        assert cp.file_path.name == "b.py"
        assert cp.tool_name == "file_write"
        assert len(tl) == 1

    def test_pop_empty(self) -> None:
        tl = CheckpointTimeline()
        assert tl.pop_last() is None

    def test_restore_last(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.py"
            p.write_text("original")
            tl = CheckpointTimeline()
            tl.capture(p, "original", "edit")
            p.write_text("modified")

            cp = tl.restore_last()
            assert cp is not None
            assert p.read_text() == "original"
            assert len(tl) == 0

    def test_max_checkpoints(self, tmp_path: Path) -> None:
        tl = CheckpointTimeline()
        for i in range(60):
            p = tmp_path / f"{i}.py"
            p.write_text(str(i))
            tl.capture(p, str(i))
        assert len(tl) == CheckpointTimeline.MAX_CHECKPOINTS

    def test_list_checkpoints(self, tmp_path: Path) -> None:
        tl = CheckpointTimeline()
        a = tmp_path / "a.py"
        a.write_text("a")
        b = tmp_path / "b.py"
        b.write_text("b")
        tl.capture(a, "a", "edit")
        tl.capture(b, "b", "file_write")
        points = tl.list_checkpoints()
        assert len(points) == 2
        assert points[0]["index"] == 0
        assert points[1]["index"] == 1
        assert points[0]["tool"] == "edit"
        assert str(b.resolve()) in points[1]["file"]


class TestUndoEditCommand:
    def test_undo_restores_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.py"
            p.write_text("original")

            tl = CheckpointTimeline()
            tl.capture(p, "original", "edit")
            p.write_text("modified")

            session = MagicMock()
            session._checkpoint_timeline = tl

            from beep.chat.commands.checkpoint import UndoEditCommand

            cmd = UndoEditCommand()
            import asyncio

            asyncio.run(cmd.execute("", {"session": session}))

            assert p.read_text() == "original"

    def test_undo_empty_timeline(self) -> None:
        session = MagicMock()
        session._checkpoint_timeline = CheckpointTimeline()

        from beep.chat.commands.checkpoint import UndoEditCommand

        cmd = UndoEditCommand()
        import asyncio

        asyncio.run(cmd.execute("", {"session": session}))

    def test_list_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.py"
            p.write_text("content")

            tl = CheckpointTimeline()
            tl.capture(p, "content", "edit")

            session = MagicMock()
            session._checkpoint_timeline = tl

            from beep.chat.commands.checkpoint import CheckpointsCommand

            cmd = CheckpointsCommand()
            import asyncio

            asyncio.run(cmd.execute("", {"session": session}))
