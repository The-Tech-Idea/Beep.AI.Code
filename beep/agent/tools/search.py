"""Search tool for agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.workspace.search import search_workspace

_MAX_RESULTS = 200


class SearchTool(BaseTool):
    """Search files for a pattern, with optional context lines around each match."""

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
        return "search"

    @property
    def description(self) -> str:
        return (
            "Search files for a regex pattern. "
            "Returns matching lines with file path and line number. "
            "Set context_lines (1-5) to see surrounding lines for each match."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (defaults to workspace root)",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g. '*.py', '*.ts')",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search is case-sensitive (default true)",
            },
            "context_lines": {
                "type": "integer",
                "description": "Number of context lines to show before and after each match (0-5, default 0)",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["path", "file_pattern", "case_sensitive", "context_lines"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        pattern: str = kwargs.get("pattern", "")
        path: str | None = kwargs.get("path")
        file_pattern: str | None = kwargs.get("file_pattern")
        case_sensitive: bool = kwargs.get("case_sensitive", True)
        context_lines: int = min(max(int(kwargs.get("context_lines", 0)), 0), 5)

        root_str = path or (str(self._workspace_root) if self._workspace_root else ".")
        root = Path(root_str).resolve()

        if self._is_outside_workspace(root):
            return ToolResult(success=False, output="", error=f"Path outside workspace: {path}")
        if not root.is_dir():
            return ToolResult(success=False, output="", error=f"Not a directory: {root_str}")

        try:
            result = search_workspace(
                root,
                pattern=pattern,
                case_sensitive=case_sensitive,
                file_pattern=file_pattern,
                context_lines=context_lines,
                max_results=_MAX_RESULTS,
            )
        except ValueError as exc:
            return ToolResult(success=False, output="", error=str(exc))

        if not result.matches:
            return ToolResult(success=True, output="No matches found")

        output = "\n".join(
            f"{match.relative_path}:{match.line_number}{'>' if match.is_match else ' '} {match.line_text}"
            for match in result.matches
        )
        if result.capped:
            output += f"\n[results capped at {_MAX_RESULTS} — narrow pattern or path to see more]"
        return ToolResult(success=True, output=output)

