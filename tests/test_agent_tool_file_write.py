"""Unit tests for FileWriteTool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.agent.tools.file_write import FileWriteTool


class TestFileWriteTool:
    @pytest.mark.asyncio
    async def test_creates_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "new.txt"
            tool = FileWriteTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f), content="hello\nworld\n")
            assert result.success
            assert f.read_text(encoding="utf-8") == "hello\nworld\n"

    @pytest.mark.asyncio
    async def test_overwrites_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "existing.txt"
            f.write_text("old content\n", encoding="utf-8")
            tool = FileWriteTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f), content="new content\n")
            assert result.success
            assert f.read_text(encoding="utf-8") == "new content\n"

    @pytest.mark.asyncio
    async def test_response_reports_byte_and_line_count(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "counted.txt"
            content = "line1\nline2\nline3\n"
            tool = FileWriteTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f), content=content)
            assert result.success
            assert str(len(content)) in result.output  # byte count
            assert "3 lines" in result.output

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "subdir" / "deep" / "file.txt"
            tool = FileWriteTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f), content="content\n")
            assert result.success
            assert f.exists()

    @pytest.mark.asyncio
    async def test_no_backup_files_created(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.py"
            f.write_text("original\n", encoding="utf-8")
            tool = FileWriteTool(workspace_root=Path(td))
            await tool.execute(file_path=str(f), content="updated\n")
            backup_files = list(Path(td).glob("*.backup.*"))
            assert backup_files == [], f"Unexpected backup files: {backup_files}"

    @pytest.mark.asyncio
    async def test_workspace_escape_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with tempfile.TemporaryDirectory() as td2:
                f = Path(td2) / "evil.txt"
                tool = FileWriteTool(workspace_root=Path(td))
                result = await tool.execute(file_path=str(f), content="evil")
                assert not result.success
                assert "outside workspace" in (result.error or "").lower()
