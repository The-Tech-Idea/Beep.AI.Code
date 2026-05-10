"""Shell command execution tool for agent."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult

_DEFAULT_TIMEOUT = 30
_MAX_TIMEOUT = 300
_MAX_OUTPUT_CHARS = 10_000


class ShellTool(BaseTool):
    """Execute a shell command in the workspace directory.

    Use for running tests, builds, git operations, package installs, linters, etc.
    Output is capped at 10 000 characters; use targeted commands or redirect output
    to a file when you need more.
    """

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root or Path.cwd()

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command in the workspace root. "
            "Use for tests, builds, git operations, linters, package management, etc. "
            f"Default timeout is {_DEFAULT_TIMEOUT}s; max is {_MAX_TIMEOUT}s."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": (
                    f"Timeout in seconds (default {_DEFAULT_TIMEOUT}, max {_MAX_TIMEOUT}). "
                    "Increase for slow build or install commands."
                ),
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["timeout"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        command: str = kwargs.get("command", "")
        raw_timeout: int = kwargs.get("timeout", _DEFAULT_TIMEOUT)
        timeout = min(max(int(raw_timeout), 1), _MAX_TIMEOUT)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._workspace_root,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout}s: {command}",
                )

            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
            exit_code = process.returncode

            combined = stdout_str
            if stderr_str:
                combined += ("\n" if combined else "") + "[stderr]\n" + stderr_str

            if len(combined) > _MAX_OUTPUT_CHARS:
                combined = combined[:_MAX_OUTPUT_CHARS] + f"\n[... output truncated at {_MAX_OUTPUT_CHARS} chars]"

            header = f"[exit_code: {exit_code}]\n"
            if exit_code == 0:
                return ToolResult(success=True, output=header + (combined or "(no output)"))
            else:
                return ToolResult(
                    success=False,
                    output=header + combined,
                    error=f"Command exited with code {exit_code}",
                )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc))

