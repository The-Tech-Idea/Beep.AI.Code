"""Tests for multi-file editing and planning."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.planner.editor import EditPlan, FileEdit, PlanStatus


class TestFileEdit:
    def test_create_edit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.py"
            f.write_text("old\n", encoding="utf-8")
            edit = FileEdit(
                file_path=f,
                old_content="old\n",
                new_content="new\n",
            )
            assert not edit.is_create
            assert not edit.is_delete
            assert not edit.applied

    def test_create_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            edit = FileEdit(
                file_path=Path(td) / "new.py",
                new_content="print('hi')\n",
            )
            assert edit.is_create

    def test_delete_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "old.py"
            f.write_text("content\n", encoding="utf-8")
            edit = FileEdit(
                file_path=f,
                old_content="content\n",
                new_content="",
            )
            assert edit.is_delete

    def test_diff_property(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            edit = FileEdit(
                file_path=Path(td) / "test.py",
                old_content="line1\nline2\n",
                new_content="line1\nmodified\n",
            )
            diff = edit.diff
            assert "line1" in diff
            assert "modified" in diff


class TestEditPlan:
    def test_create_plan(self) -> None:
        plan = EditPlan(goal="Add logging")
        assert plan.status == PlanStatus.DRAFT
        assert plan.edits == []

    def test_add_edit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan = EditPlan(goal="Update files")
            plan.add_edit(
                file_path=Path(td) / "test.py",
                old_content="old\n",
                new_content="new\n",
            )
            assert len(plan.edits) == 1

    @pytest.mark.asyncio
    async def test_execute_with_confirm_denied(self) -> None:
        import unittest.mock

        with tempfile.TemporaryDirectory() as td:
            plan = EditPlan(goal="Test")
            plan.add_edit(
                file_path=Path(td) / "test.py",
                old_content="old\n",
                new_content="new\n",
            )
            with unittest.mock.patch(
                "rich.prompt.Confirm.ask", return_value=False
            ):
                result = await plan.execute(require_confirm=True)
            assert result is False

    @pytest.mark.asyncio
    async def test_execute_create_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan = EditPlan(goal="Create file")
            plan.add_edit(
                file_path=Path(td) / "new.py",
                old_content="",
                new_content="print('created')\n",
            )
            result = await plan.execute(require_confirm=False)
            assert result is True
            assert (Path(td) / "new.py").exists()

    @pytest.mark.asyncio
    async def test_execute_edit_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.py"
            f.write_text("old content\n", encoding="utf-8")
            plan = EditPlan(goal="Edit file")
            plan.add_edit(
                file_path=f,
                old_content="old content\n",
                new_content="new content\n",
            )
            result = await plan.execute(require_confirm=False)
            assert result is True
            assert f.read_text(encoding="utf-8") == "new content\n"

    @pytest.mark.asyncio
    async def test_execute_delete_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "delete.py"
            f.write_text("to delete\n", encoding="utf-8")
            plan = EditPlan(goal="Delete file")
            plan.add_edit(
                file_path=f,
                old_content="to delete\n",
                new_content="",
            )
            result = await plan.execute(require_confirm=False)
            assert result is True
            assert not f.exists()

    @pytest.mark.asyncio
    async def test_rollback_create(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan = EditPlan(goal="Create and rollback")
            fp = Path(td) / "temp.py"
            plan.add_edit(
                file_path=fp,
                old_content="",
                new_content="temporary\n",
            )
            await plan.execute(require_confirm=False)
            assert fp.exists()

            await plan.rollback()
            # After creation, is_create is False so rollback writes old_content
            assert fp.read_text(encoding="utf-8") == ""
            assert plan.status == PlanStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_edit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "edit.py"
            f.write_text("original\n", encoding="utf-8")
            plan = EditPlan(goal="Edit and rollback")
            plan.add_edit(
                file_path=f,
                old_content="original\n",
                new_content="modified\n",
            )
            await plan.execute(require_confirm=False)
            assert f.read_text(encoding="utf-8") == "modified\n"

            await plan.rollback()
            assert f.read_text(encoding="utf-8") == "original\n"

    @pytest.mark.asyncio
    async def test_rollback_delete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "restore.py"
            f.write_text("important\n", encoding="utf-8")
            plan = EditPlan(goal="Delete and rollback")
            plan.add_edit(
                file_path=f,
                old_content="important\n",
                new_content="",
            )
            await plan.execute(require_confirm=False)
            assert not f.exists()

            await plan.rollback()
            assert f.exists()
            assert f.read_text(encoding="utf-8") == "important\n"

    def test_plan_status_transitions(self) -> None:
        plan = EditPlan(goal="Test")
        assert plan.status == PlanStatus.DRAFT
        plan.status = PlanStatus.APPROVED
        assert plan.status == PlanStatus.APPROVED

    @pytest.mark.asyncio
    async def test_multi_file_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan = EditPlan(goal="Refactor")
            for i in range(3):
                plan.add_edit(
                    file_path=Path(td) / f"file{i}.py",
                    old_content="",
                    new_content=f"# File {i}\n",
                )
            assert len(plan.edits) == 3
            result = await plan.execute(require_confirm=False)
            assert result is True
            for i in range(3):
                assert (Path(td) / f"file{i}.py").exists()

    def test_plan_display(self, capsys: pytest.CaptureFixture) -> None:
        plan = EditPlan(goal="Test display")
        plan.add_edit(
            file_path=Path("test.py"),
            old_content="old\n",
            new_content="new line 1\nnew line 2\n",
        )
        plan.display()
        captured = capsys.readouterr()
        assert "Test display" in captured.out
        assert "test.py" in captured.out
