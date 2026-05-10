"""File read tool for agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.workspace.binary_detector import is_binary_file
from beep.workspace.file_ops import read_lines

_MAX_LINES_PER_READ = 300


class FileReadTool(BaseTool):
    """Read file contents with optional line range.

    For large files always use start_line/end_line to read in pages.
    The response header reports total_lines so you know how many pages remain.
    """

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root.resolve() if workspace_root else None

    def _is_outside_workspace(self, path: Path) -> bool:
        return bool(
            self._workspace_root
            and self._workspace_root not in path.parents
            and path != self._workspace_root
        )

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file. "
            f"Returns at most {_MAX_LINES_PER_READ} lines per call. "
            "For large files use start_line and end_line to paginate; "
            "the response header shows total_lines so you know what remains."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read",
            },
            "start_line": {
                "type": "integer",
                "description": "First line to read, 1-indexed (optional)",
            },
            "end_line": {
                "type": "integer",
                "description": "Last line to read, 1-indexed (optional)",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["start_line", "end_line"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs.get("file_path", "")
        start_line: int | None = kwargs.get("start_line")
        end_line: int | None = kwargs.get("end_line")

        path = Path(file_path).resolve()
        if self._is_outside_workspace(path):
            return ToolResult(success=False, output="", error=f"Path outside workspace: {file_path}")
        if not path.exists():
            return ToolResult(success=False, output="", error=f"File not found: {file_path}")
        if not path.is_file():
            return ToolResult(success=False, output="", error=f"Not a file: {file_path}")
        if is_binary_file(path):
            return ToolResult(success=False, output="", error=f"Binary file not supported: {file_path}")

        try:
            effective_start = max(1, start_line or 1)
            capped_end = effective_start + _MAX_LINES_PER_READ - 1
            effective_requested_end = capped_end if end_line is None else min(end_line, capped_end)
            lines, total_lines = read_lines(
                path,
                start=effective_start,
                end=effective_requested_end,
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc))

        effective_end = min(effective_requested_end, total_lines)
        truncated = (
            total_lines > effective_requested_end
            if end_line is None
            else end_line > effective_requested_end
        )
        header = (
            f"[file: {file_path}  total_lines: {total_lines}  "
            f"showing: {effective_start}-{effective_end}"
            + ("  (truncated — use start_line/end_line to read more)" if truncated else "")
            + "]\n"
        )

        numbered = []
        for index, line in enumerate(lines):
            numbered.append(f"{effective_start + index:4d} | {line}")
        content = "\n".join(numbered)
        return ToolResult(success=True, output=header + content)

