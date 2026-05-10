"""File write tool for agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.workspace.file_ops import write_file


class FileWriteTool(BaseTool):
    """Write or overwrite a file.

    Prefer file_edit for targeted changes to existing files; use file_write
    only when creating a new file or replacing the entire content.
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
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "Write content to a file, creating it (and any missing parent directories) if needed, "
            "or overwriting the entire file if it already exists. "
            "For surgical edits to existing files use file_edit instead."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "Full content to write to the file",
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs.get("file_path", "")
        content_str: str = kwargs.get("content", "")
        path = Path(file_path).resolve()
        if self._is_outside_workspace(path):
            return ToolResult(success=False, output="", error=f"Path outside workspace: {file_path}")
        try:
            write_file(path, content_str, create_backup=False)
            line_count = content_str.count("\n") + (1 if content_str and not content_str.endswith("\n") else 0)
            return ToolResult(
                success=True,
                output=f"Wrote {len(content_str)} bytes ({line_count} lines) to {file_path}",
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc))

