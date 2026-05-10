"""Unit tests for FileReadTool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.agent.tools.file_read import FileReadTool, _MAX_LINES_PER_READ


class TestFileReadTool:
    @pytest.mark.asyncio
    async def test_reads_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "hello.txt"
            f.write_text("hello world\n", encoding="utf-8")
            tool = FileReadTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f))
            assert result.success
            assert "hello world" in result.output

    @pytest.mark.asyncio
    async def test_response_includes_total_lines_header(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "data.txt"
            f.write_text("\n".join(str(i) for i in range(10)) + "\n", encoding="utf-8")
            tool = FileReadTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f))
            assert result.success
            assert "total_lines: 10" in result.output

    @pytest.mark.asyncio
    async def test_start_and_end_line_params(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "lines.txt"
            lines = [f"line{i}" for i in range(1, 11)]
            f.write_text("\n".join(lines) + "\n", encoding="utf-8")
            tool = FileReadTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f), start_line=3, end_line=5)
            assert result.success
            assert "showing: 3-5" in result.output
            assert "line3" in result.output
            assert "line5" in result.output
            assert "line1" not in result.output
            assert "line6" not in result.output

    @pytest.mark.asyncio
    async def test_cap_enforced_at_max_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "big.txt"
            f.write_text("\n".join(str(i) for i in range(_MAX_LINES_PER_READ + 50)) + "\n", encoding="utf-8")
            tool = FileReadTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f))
            assert result.success
            # Header shows showing range capped at _MAX_LINES_PER_READ
            assert f"showing: 1-{_MAX_LINES_PER_READ}" in result.output
            # Truncation notice present
            assert "truncated" in result.output

    @pytest.mark.asyncio
    async def test_optional_params_declared(self) -> None:
        tool = FileReadTool()
        assert "start_line" in tool.optional_params
        assert "end_line" in tool.optional_params

    @pytest.mark.asyncio
    async def test_required_param_in_schema(self) -> None:
        tool = FileReadTool()
        defn = tool.to_openai_tool()
        required = defn["function"]["parameters"].get("required", [])
        assert "file_path" in required
        assert "start_line" not in required
        assert "end_line" not in required

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = FileReadTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(Path(td) / "nope.txt"))
            assert not result.success
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_workspace_escape_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with tempfile.TemporaryDirectory() as td2:
                f = Path(td2) / "secret.txt"
                f.write_text("secret", encoding="utf-8")
                tool = FileReadTool(workspace_root=Path(td))
                result = await tool.execute(file_path=str(f))
                assert not result.success
                assert "outside workspace" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_uses_shared_read_lines_for_pagination(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "hello.txt"
            f.write_text("placeholder\n", encoding="utf-8")
            calls: list[tuple[Path, int | None, int | None]] = []

            def _fake_read_lines(path: Path, start: int | None = None, end: int | None = None) -> tuple[list[str], int]:
                calls.append((path, start, end))
                return (["line3", "line4", "line5"], 10)

            monkeypatch.setattr("beep.agent.tools.file_read.read_lines", _fake_read_lines)

            tool = FileReadTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f), start_line=3, end_line=5)

            assert result.success
            assert calls == [(f.resolve(), 3, 5)]
            assert "total_lines: 10" in result.output
            assert "line3" in result.output
            assert "line5" in result.output
