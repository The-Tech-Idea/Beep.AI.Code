"""List directory tool for agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.workspace.ignore import IgnoreMatcher

_MAX_ENTRIES = 500


class ListDirectoryTool(BaseTool):
    """List the contents of a directory.

    Use this before reading files to understand the project structure.
    Ignored directories (node_modules, .venv, __pycache__, etc.) are skipped
    unless the path is explicitly inside one of them.
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
        return "list_directory"

    @property
    def description(self) -> str:
        return (
            "List files and subdirectories at a path. "
            "Omit path to list the workspace root. "
            "Set recursive=true for a full subtree (depth-first, ignores common noise dirs). "
            "Use glob_files for pattern-based file search instead."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "Directory to list (defaults to workspace root)",
            },
            "recursive": {
                "type": "boolean",
                "description": "List recursively (default false)",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["path", "recursive"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        path_str: str | None = kwargs.get("path")
        recursive: bool = kwargs.get("recursive", False)

        root_str = path_str or (str(self._workspace_root) if self._workspace_root else ".")
        target = Path(root_str).resolve()

        if self._is_outside_workspace(target):
            return ToolResult(success=False, output="", error=f"Path outside workspace: {root_str}")
        if not target.exists():
            return ToolResult(success=False, output="", error=f"Path not found: {root_str}")
        if not target.is_dir():
            return ToolResult(success=False, output="", error=f"Not a directory: {root_str}")

        matcher = IgnoreMatcher(target)
        lines: list[str] = [f"{target}/"]
        count = 0

        if recursive:
            for entry in sorted(target.rglob("*")):
                if matcher.is_ignored(entry):
                    continue
                rel = entry.relative_to(target)
                suffix = "/" if entry.is_dir() else ""
                lines.append(f"  {rel}{suffix}")
                count += 1
                if count >= _MAX_ENTRIES:
                    lines.append(f"  [... listing capped at {_MAX_ENTRIES} entries]")
                    break
        else:
            try:
                entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError as exc:
                return ToolResult(success=False, output="", error=str(exc))

            for entry in entries:
                if matcher.is_ignored(entry):
                    continue
                suffix = "/" if entry.is_dir() else ""
                lines.append(f"  {entry.name}{suffix}")

        return ToolResult(success=True, output="\n".join(lines))
