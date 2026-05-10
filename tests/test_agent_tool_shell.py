"""Unit tests for ShellTool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.agent.tools.shell import ShellTool, _MAX_OUTPUT_CHARS


class TestShellTool:
    @pytest.mark.asyncio
    async def test_exit_code_header_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            result = await tool.execute(command="echo hello")
            assert result.success
            assert result.output.startswith("[exit_code: 0]")

    @pytest.mark.asyncio
    async def test_stdout_present_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            result = await tool.execute(command="echo hello_marker")
            assert result.success
            assert "hello_marker" in result.output

    @pytest.mark.asyncio
    async def test_nonzero_exit_code_reported(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            result = await tool.execute(command="exit 42", timeout=5)
            assert not result.success
            assert "[exit_code: 42]" in result.output

    @pytest.mark.asyncio
    async def test_stderr_visible_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            # Write to stderr explicitly
            result = await tool.execute(command='python -c "import sys; sys.stderr.write(\'err_marker\\n\')"')
            # stderr should be captured under [stderr] header regardless of exit code
            assert "[stderr]" in result.output
            assert "err_marker" in result.output

    @pytest.mark.asyncio
    async def test_output_capped_at_max_chars(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            # Generate output larger than the cap
            big_cmd = f'python -c "print(\'x\' * {_MAX_OUTPUT_CHARS + 500})"'
            result = await tool.execute(command=big_cmd)
            assert result.output is not None
            assert "truncated" in result.output

    @pytest.mark.asyncio
    async def test_timeout_param_is_optional(self) -> None:
        tool = ShellTool()
        assert "timeout" in tool.optional_params

    @pytest.mark.asyncio
    async def test_timeout_param_not_in_required(self) -> None:
        tool = ShellTool()
        defn = tool.to_openai_tool()
        required = defn["function"]["parameters"].get("required", [])
        assert "timeout" not in required
        assert "command" in required
