"""Tests for agent tools."""

import asyncio
import tempfile
from pathlib import Path

from beep.agent.tools.base import ToolResult
from beep.agent.tools.file_read import FileReadTool
from beep.agent.tools.file_write import FileWriteTool


def test_tool_result_success():
    """Test ToolResult creation."""
    result = ToolResult(success=True, output="done")
    assert result.success
    assert result.output == "done"
    assert result.error is None
    assert not result.is_error


def test_tool_result_error():
    """Test ToolResult error state."""
    result = ToolResult(success=False, output="", error="failed")
    assert not result.success
    assert result.error == "failed"


def test_file_read_tool():
    """Test file read tool."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.py"
        f.write_text("def hello():\n    print('world')\n")
        tool = FileReadTool()
        result = asyncio.run(tool.execute(file_path=str(f)))
        assert result.success
        assert "def hello()" in result.output


def test_file_read_tool_missing_file():
    """Test file read tool with missing file."""
    tool = FileReadTool()
    result = asyncio.run(tool.execute(file_path="C:\\nonexistent\\file.py"))
    assert not result.success
    assert "not found" in result.error.lower()


def test_file_read_tool_with_lines():
    """Test file read tool with line range."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.py"
        f.write_text("def hello():\n    print('world')\n")
        tool = FileReadTool()
        result = asyncio.run(tool.execute(file_path=str(f), start_line=1, end_line=1))
        assert result.success
        assert "def hello()" in result.output


def test_file_write_tool():
    """Test file write tool."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "output.py"
        tool = FileWriteTool()
        result = asyncio.run(tool.execute(file_path=str(path), content="print('test')"))
        assert result.success
        assert path.exists()
        assert path.read_text() == "print('test')"
