"""Tests for FileEditTool and SingleEditTool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.agent.tools.file_edit import FileEditTool, SingleEditTool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEARCH_REPLACE_BLOCK = """\
<<<<<<< SEARCH
old content
=======
new content
>>>>>>> REPLACE"""


# ---------------------------------------------------------------------------
# FileEditTool
# ---------------------------------------------------------------------------


class TestFileEditTool:
    @pytest.mark.asyncio
    async def test_applies_search_replace_block(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "code.py"
            f.write_text("old content\n", encoding="utf-8")
            tool = FileEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(f),
                edit=_SEARCH_REPLACE_BLOCK,
            )
            assert result.success, result.error
            assert "new content" in f.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_applied_content_is_correct(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "src.py"
            f.write_text("def foo():\n    pass\n", encoding="utf-8")
            tool = FileEditTool(workspace_root=Path(td))
            edit = (
                "<<<<<<< SEARCH\n"
                "def foo():\n"
                "    pass\n"
                "=======\n"
                "def foo():\n"
                "    return 42\n"
                ">>>>>>> REPLACE"
            )
            result = await tool.execute(file_path=str(f), edit=edit)
            assert result.success, result.error
            assert "return 42" in f.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_no_match_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "x.py"
            f.write_text("completely different\n", encoding="utf-8")
            tool = FileEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(f),
                edit=_SEARCH_REPLACE_BLOCK,
            )
        assert not result.success

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = FileEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(Path(td) / "missing.py"),
                edit=_SEARCH_REPLACE_BLOCK,
            )
        assert not result.success
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_workspace_escape_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td).parent / "escape.py"
            tool = FileEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(outside),
                edit=_SEARCH_REPLACE_BLOCK,
            )
        assert not result.success
        assert "workspace" in (result.error or "").lower()

    def test_tool_name(self) -> None:
        assert FileEditTool().name == "file_edit"

    def test_description_warns_about_whitespace_sensitivity(self) -> None:
        assert "whitespace-sensitive" in FileEditTool().description

    def test_schema_has_required_params(self) -> None:
        schema = FileEditTool().to_openai_tool()
        required = schema["function"]["parameters"]["required"]
        assert "file_path" in required
        assert "edit" in required

    @pytest.mark.asyncio
    async def test_multiple_blocks_applied(self) -> None:
        """Two SEARCH/REPLACE blocks in one edit must both apply."""
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "multi.py"
            f.write_text("alpha\nbeta\n", encoding="utf-8")
            tool = FileEditTool(workspace_root=Path(td))
            edit = (
                "<<<<<<< SEARCH\n"
                "alpha\n"
                "=======\n"
                "ALPHA\n"
                ">>>>>>> REPLACE\n"
                "<<<<<<< SEARCH\n"
                "beta\n"
                "=======\n"
                "BETA\n"
                ">>>>>>> REPLACE"
            )
            result = await tool.execute(file_path=str(f), edit=edit)
            assert result.success, result.error
            text = f.read_text(encoding="utf-8")
            assert "ALPHA" in text
            assert "BETA" in text

    @pytest.mark.asyncio
    async def test_failed_edit_keeps_full_feedback_in_output_and_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "fail.py"
            f.write_text("unchanged\n", encoding="utf-8")
            tool = FileEditTool(workspace_root=Path(td))

            result = await tool.execute(file_path=str(f), edit=_SEARCH_REPLACE_BLOCK)

        assert not result.success
        assert result.output
        assert result.error
        assert result.output in result.error


# ---------------------------------------------------------------------------
# SingleEditTool
# ---------------------------------------------------------------------------


class TestSingleEditTool:
    @pytest.mark.asyncio
    async def test_applies_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "s.py"
            f.write_text("hello world\n", encoding="utf-8")
            tool = SingleEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(f),
                search="hello world",
                replace="goodbye world",
            )
            assert result.success, result.error
            assert "goodbye world" in f.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_no_match_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "s.py"
            f.write_text("nothing matches here\n", encoding="utf-8")
            tool = SingleEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(f),
                search="xyz abc",
                replace="replacement",
            )
        assert not result.success

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = SingleEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(Path(td) / "ghost.py"),
                search="x",
                replace="y",
            )
        assert not result.success
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_workspace_escape_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td).parent / "escape2.py"
            tool = SingleEditTool(workspace_root=Path(td))
            result = await tool.execute(
                file_path=str(outside),
                search="x",
                replace="y",
            )
        assert not result.success
        assert "workspace" in (result.error or "").lower()

    def test_tool_name(self) -> None:
        assert SingleEditTool().name == "single_edit"

    def test_schema_has_required_params(self) -> None:
        schema = SingleEditTool().to_openai_tool()
        required = schema["function"]["parameters"]["required"]
        assert "file_path" in required
        assert "search" in required
        assert "replace" in required
