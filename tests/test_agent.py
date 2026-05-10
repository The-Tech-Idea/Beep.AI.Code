"""Tests for agent loop and tools."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.agent.approval import requires_approval
from beep.agent.graph_support import _format_tool_result as format_tool_result
from beep.agent.tools.base import ToolResult
from beep.agent.tools.factory import get_default_tools
from beep.agent.tools.file_read import FileReadTool
from beep.agent.tools.file_write import FileWriteTool
from beep.agent.tools.search import SearchTool
from beep.agent.tools.shell import ShellTool


class TestToolResult:
    def test_success(self) -> None:
        result = ToolResult(success=True, output="done")
        assert result.success
        assert result.output == "done"

    def test_error(self) -> None:
        result = ToolResult(success=False, output="", error="failed")
        assert not result.success
        assert result.error == "failed"


class TestApproval:
    def test_file_read_no_approval(self) -> None:
        assert requires_approval("file_read") is False

    def test_search_no_approval(self) -> None:
        assert requires_approval("search") is False

    def test_file_write_requires_approval(self) -> None:
        assert requires_approval("file_write") is True

    def test_file_edit_requires_approval(self) -> None:
        assert requires_approval("file_edit") is True

    def test_shell_requires_approval(self) -> None:
        assert requires_approval("shell") is True


class TestDefaultTools:
    def test_get_default_tools(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tools = get_default_tools(Path(td))
            assert len(tools) == 12
            names = {t.name for t in tools}
            assert "file_read" in names
            assert "file_write" in names
            assert "file_edit" in names
            assert "single_edit" in names
            assert "search" in names
            assert "shell" in names
            assert "list_directory" in names
            assert "glob_files" in names
            assert "git" in names
            assert "read_files" in names
            assert "todo_write" in names
            assert "dispatch_agent" in names

    def test_get_default_tools_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tools = get_default_tools(Path(td), read_only=True)
            assert len(tools) == 8
            names = {t.name for t in tools}
            assert "file_read" in names
            assert "search" in names
            assert "list_directory" in names
            assert "glob_files" in names
            assert "git" in names
            assert "read_files" in names
            assert "file_write" not in names
            assert "file_edit" not in names
            assert "shell" not in names


class TestFileReadTool:
    @pytest.mark.asyncio
    async def test_read_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.py"
            f.write_text("hello world\n", encoding="utf-8")
            tool = FileReadTool()
            result = await tool.execute(file_path=str(f))
            assert result.success
            assert "hello world" in result.output

    @pytest.mark.asyncio
    async def test_read_with_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.py"
            f.write_text("line1\nline2\nline3\n", encoding="utf-8")
            tool = FileReadTool()
            result = await tool.execute(file_path=str(f), start_line=2, end_line=3)
            assert result.success
            assert "line2" in result.output

    @pytest.mark.asyncio
    async def test_read_missing_file(self) -> None:
        tool = FileReadTool()
        result = await tool.execute(file_path="/nonexistent/file.py")
        assert not result.success
        assert "not found" in result.error.lower() or "outside workspace" in result.error.lower()

    @pytest.mark.asyncio
    async def test_workspace_boundary_for_read(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = FileReadTool(workspace_root=Path(td))
            outside = Path(td).parent / "outside.txt"
            result = await tool.execute(file_path=str(outside))
            assert not result.success
            assert "outside workspace" in (result.error or "").lower()


class TestFileWriteTool:
    @pytest.mark.asyncio
    async def test_write_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "new.py"
            tool = FileWriteTool()
            result = await tool.execute(file_path=str(f), content="print('hi')\n")
            assert result.success
            assert f.read_text(encoding="utf-8") == "print('hi')\n"

    @pytest.mark.asyncio
    async def test_overwrite_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "old.py"
            f.write_text("old content\n", encoding="utf-8")
            tool = FileWriteTool()
            result = await tool.execute(file_path=str(f), content="new content\n")
            assert result.success
            assert f.read_text(encoding="utf-8") == "new content\n"


class TestSearchTool:
    @pytest.mark.asyncio
    async def test_search_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.py"
            f.write_text("def hello():\n    pass\n", encoding="utf-8")
            tool = SearchTool()
            result = await tool.execute(pattern="def hello", path=str(td))
            assert result.success

    @pytest.mark.asyncio
    async def test_search_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.py"
            f.write_text("def hello():\n    pass\n", encoding="utf-8")
            tool = SearchTool()
            result = await tool.execute(pattern="nonexistent", path=str(td))
            assert result.success
            assert "No matches" in result.output

    @pytest.mark.asyncio
    async def test_workspace_boundary_for_search(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tool = SearchTool(workspace_root=root)
            outside_dir = root.parent
            result = await tool.execute(pattern="x", path=str(outside_dir))
            assert not result.success
            assert "outside workspace" in (result.error or "").lower()


class TestShellTool:
    @pytest.mark.asyncio
    async def test_echo_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            result = await tool.execute(command="echo hello")
            assert result.success
            assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_failed_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            result = await tool.execute(command="exit 1")
            assert not result.success


class TestFormatToolResult:
    def test_format_success(self, capsys: pytest.CaptureFixture) -> None:
        result = ToolResult(success=True, output="done")
        format_tool_result("test_tool", result, 1)
        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_format_error(self, capsys: pytest.CaptureFixture) -> None:
        result = ToolResult(success=False, output="", error="failed")
        format_tool_result("test_tool", result, 1)
        captured = capsys.readouterr()
        assert "FAILED" in captured.out
