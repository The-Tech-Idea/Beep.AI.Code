"""Unit tests for SearchTool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.agent.tools.search import SearchTool, _MAX_RESULTS


class TestSearchTool:
    @pytest.mark.asyncio
    async def test_finds_match_in_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.py").write_text("def hello():\n    pass\n", encoding="utf-8")
            (Path(td) / "b.py").write_text("def world():\n    pass\n", encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="hello", path=td)
            assert result.success
            assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_match_line_has_gt_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "f.py").write_text("needle\n", encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="needle", path=td)
            assert result.success
            assert "> needle" in result.output

    @pytest.mark.asyncio
    async def test_no_match_returns_no_matches_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "f.py").write_text("nothing here\n", encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="xyz_not_present", path=td)
            assert result.success
            assert "No matches found" in result.output

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "g.py").write_text("HELLO_UPPER\n", encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="hello_upper", path=td, case_sensitive=False)
            assert result.success
            assert "HELLO_UPPER" in result.output

    @pytest.mark.asyncio
    async def test_case_sensitive_does_not_match_wrong_case(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "h.py").write_text("HELLO_UPPER\n", encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="hello_upper", path=td, case_sensitive=True)
            assert result.success
            assert "No matches found" in result.output

    @pytest.mark.asyncio
    async def test_context_lines_returns_surrounding_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            content = "before\nmatch_line\nafter\n"
            (Path(td) / "ctx.py").write_text(content, encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="match_line", path=td, context_lines=1)
            assert result.success
            assert "before" in result.output
            assert "match_line" in result.output
            assert "after" in result.output

    @pytest.mark.asyncio
    async def test_context_lines_prefix_distinguishes_match_vs_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            content = "ctx_before\ntarget_match\nctx_after\n"
            (Path(td) / "p.py").write_text(content, encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="target_match", path=td, context_lines=1)
            assert result.success
            lines_out = result.output.splitlines()
            match_lines = [l for l in lines_out if "target_match" in l]
            ctx_lines = [l for l in lines_out if "ctx_before" in l or "ctx_after" in l]
            assert all(">" in l for l in match_lines)
            assert all(">" not in l for l in ctx_lines)

    @pytest.mark.asyncio
    async def test_file_pattern_filters_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.py").write_text("keyword\n", encoding="utf-8")
            (Path(td) / "b.txt").write_text("keyword\n", encoding="utf-8")
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="keyword", path=td, file_pattern="*.py")
            assert result.success
            assert "a.py" in result.output
            assert "b.txt" not in result.output

    @pytest.mark.asyncio
    async def test_optional_params_declared(self) -> None:
        tool = SearchTool()
        optional = tool.optional_params
        assert "path" in optional
        assert "file_pattern" in optional
        assert "case_sensitive" in optional
        assert "context_lines" in optional

    @pytest.mark.asyncio
    async def test_pattern_required_in_schema(self) -> None:
        tool = SearchTool()
        defn = tool.to_openai_tool()
        required = defn["function"]["parameters"].get("required", [])
        assert "pattern" in required
        assert "path" not in required

    @pytest.mark.asyncio
    async def test_invalid_regex_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = SearchTool(workspace_root=Path(td))
            result = await tool.execute(pattern="[unclosed", path=td)
            assert not result.success
            assert "Invalid regex" in (result.error or "")
