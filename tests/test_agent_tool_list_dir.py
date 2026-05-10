"""Unit tests for ListDirectoryTool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.agent.tools.list_directory import ListDirectoryTool


class TestListDirectoryTool:
    @pytest.mark.asyncio
    async def test_lists_immediate_children(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "file_a.txt").write_text("a", encoding="utf-8")
            (Path(td) / "file_b.py").write_text("b", encoding="utf-8")
            tool = ListDirectoryTool(workspace_root=Path(td))
            result = await tool.execute(path=td)
            assert result.success
            assert "file_a.txt" in result.output
            assert "file_b.py" in result.output

    @pytest.mark.asyncio
    async def test_directories_have_slash_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sub = Path(td) / "subdir"
            sub.mkdir()
            tool = ListDirectoryTool(workspace_root=Path(td))
            result = await tool.execute(path=td)
            assert result.success
            assert "subdir/" in result.output

    @pytest.mark.asyncio
    async def test_recursive_lists_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sub = Path(td) / "pkg"
            sub.mkdir()
            (sub / "module.py").write_text("x", encoding="utf-8")
            tool = ListDirectoryTool(workspace_root=Path(td))
            result = await tool.execute(path=td, recursive=True)
            assert result.success
            assert "module.py" in result.output

    @pytest.mark.asyncio
    async def test_ignored_pyc_files_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            # *.pyc is in the DEFAULT_PATTERNS ignore list
            (Path(td) / "module.pyc").write_text("", encoding="utf-8")
            (Path(td) / "real_file.py").write_text("x", encoding="utf-8")
            tool = ListDirectoryTool(workspace_root=Path(td))
            result = await tool.execute(path=td, recursive=True)
            assert result.success
            assert "real_file.py" in result.output
            assert "module.pyc" not in result.output

    @pytest.mark.asyncio
    async def test_defaults_to_workspace_root_when_no_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "root_file.txt").write_text("x", encoding="utf-8")
            tool = ListDirectoryTool(workspace_root=Path(td))
            result = await tool.execute()
            assert result.success
            assert "root_file.txt" in result.output

    @pytest.mark.asyncio
    async def test_path_and_recursive_are_optional(self) -> None:
        tool = ListDirectoryTool()
        optional = tool.optional_params
        assert "path" in optional
        assert "recursive" in optional

    @pytest.mark.asyncio
    async def test_workspace_escape_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with tempfile.TemporaryDirectory() as td2:
                tool = ListDirectoryTool(workspace_root=Path(td))
                result = await tool.execute(path=td2)
                assert not result.success
                assert "outside workspace" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_nonexistent_path_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ListDirectoryTool(workspace_root=Path(td))
            result = await tool.execute(path=str(Path(td) / "no_such_dir"))
            assert not result.success
            assert result.error is not None
