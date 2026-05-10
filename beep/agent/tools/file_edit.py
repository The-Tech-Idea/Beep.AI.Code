"""File edit tool for agent (SEARCH/REPLACE + patch-based)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.workspace.search_replace import (
    apply_blocks_from_text,
    apply_search_replace_file,
)


class _WorkspaceGuard:
    """Shared workspace path guard for file mutation tools."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root.resolve() if workspace_root else None

    def _is_outside_workspace(self, path: Path) -> bool:
        """Check if path is outside the workspace directory."""
        return bool(
            self._workspace_root
            and self._workspace_root not in path.parents
            and path != self._workspace_root
        )


class FileEditTool(_WorkspaceGuard, BaseTool):
    """Edit a file using SEARCH/REPLACE blocks.

    Supports:
    - <<<<<<< SEARCH / ======= / >>>>>>> REPLACE blocks
    - Fuzzy matching with whitespace tolerance
    - Multiple blocks in a single edit
    """

    @property
    def name(self) -> str:
        return "file_edit"

    @property
    def description(self) -> str:
        return (
            "Edit a file using SEARCH/REPLACE blocks. "
            "Wrap the text to find in <<<<<<< SEARCH ... ======= "
            "and the replacement in ... >>>>>>> REPLACE. "
            "Multiple blocks can be used for multi-location edits. "
            "SEARCH content is whitespace-sensitive in practice, so copy the target text exactly when possible."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "edit": {
                "type": "string",
                "description": (
                    "SEARCH/REPLACE blocks. Format:\n"
                    "<<<<<<< SEARCH\n"
                    "text to find\n"
                    "=======\n"
                    "replacement text\n"
                    ">>>>>>> REPLACE"
                ),
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs.get("file_path", "")
        edit: str = kwargs.get("edit", "")
        path = Path(file_path).resolve()
        if self._is_outside_workspace(path):
            return ToolResult(
                success=False,
                output="",
                error=f"Path outside workspace: {file_path}",
            )
        if not path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {file_path}",
            )

        try:
            original = path.read_text(encoding="utf-8")
            new_content, messages = apply_blocks_from_text(original, edit)
            feedback = "\n".join(messages)

            if new_content == original:
                return ToolResult(
                    success=False,
                    output=feedback,
                    error="No changes applied:\n" + feedback,
                )

            path.write_text(new_content, encoding="utf-8")

            success = all("FAILED" not in m for m in messages)
            return ToolResult(
                success=success,
                output=f"Edited {file_path}:\n" + feedback,
                error=("Some SEARCH/REPLACE blocks failed to apply:\n" + feedback)
                if not success
                else "",
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc))


class SingleEditTool(_WorkspaceGuard, BaseTool):
    """Simple single search/replace edit."""

    @property
    def name(self) -> str:
        return "single_edit"

    @property
    def description(self) -> str:
        return "Replace a single text block in a file with fuzzy matching."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "search": {
                "type": "string",
                "description": "Text to find (fuzzy match supported)",
            },
            "replace": {
                "type": "string",
                "description": "Replacement text",
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs.get("file_path", "")
        search: str = kwargs.get("search", "")
        replace: str = kwargs.get("replace", "")
        path = Path(file_path).resolve()
        if self._is_outside_workspace(path):
            return ToolResult(
                success=False,
                output="",
                error=f"Path outside workspace: {file_path}",
            )
        if not path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {file_path}",
            )

        success, msg = apply_search_replace_file(path, search, replace)
        return ToolResult(success=success, output=msg, error="" if success else msg)
