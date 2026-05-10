"""Glob file search tool for agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.workspace.ignore import IgnoreMatcher

_MAX_RESULTS = 500


class GlobFilesTool(BaseTool):
    """Find files whose path matches a glob pattern.

    Use this to locate files by name or extension without reading directory
    trees manually. Examples:
      pattern="**/*.py"          → all Python files
      pattern="src/**/*.ts"      → TypeScript under src/
      pattern="**/test_*.py"     → all test files
      pattern="config.*"         → any config file in the workspace root

    Returns workspace-relative paths, one per line, up to 500 results.
    Ignored directories (.git, node_modules, .venv, etc.) are excluded.
    """

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root.resolve() if workspace_root else None

    @property
    def name(self) -> str:
        return "glob_files"

    @property
    def description(self) -> str:
        return (
            "Find files matching a glob pattern (e.g. '**/*.py', 'src/**/*.ts'). "
            "Returns workspace-relative paths. "
            "Use to discover files by name/extension before reading them. "
            "Ignored directories are excluded."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "pattern": {
                "type": "string",
                "description": (
                    "Glob pattern relative to workspace root. "
                    "Examples: '**/*.py', 'src/**/*.ts', '**/test_*.py'"
                ),
            },
            "path": {
                "type": "string",
                "description": (
                    "Subdirectory to search within (defaults to workspace root). "
                    "Use to narrow results, e.g. path='src' with pattern='**/*.py'."
                ),
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["path"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        pattern: str = kwargs.get("pattern", "")
        path_arg: str | None = kwargs.get("path")

        if not pattern:
            return ToolResult(success=False, output="", error="pattern is required")

        root = self._workspace_root or Path.cwd()

        if path_arg:
            search_root = Path(path_arg)
            if not search_root.is_absolute():
                search_root = root / search_root
            search_root = search_root.resolve()
            # Sandbox: must be inside workspace
            if self._workspace_root and not (
                search_root == self._workspace_root
                or self._workspace_root in search_root.parents
            ):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path outside workspace: {path_arg}",
                )
        else:
            search_root = root

        if not search_root.exists() or not search_root.is_dir():
            return ToolResult(
                success=False,
                output="",
                error=f"Directory not found: {search_root}",
            )

        matcher = IgnoreMatcher(root)

        try:
            matched: list[str] = []
            for p in sorted(search_root.glob(pattern)):
                if not p.is_file():
                    continue
                if matcher.is_ignored(p):
                    continue
                try:
                    rel = p.relative_to(root)
                except ValueError:
                    rel = p
                matched.append(str(rel).replace("\\", "/"))
                if len(matched) >= _MAX_RESULTS:
                    break
        except ValueError as exc:
            return ToolResult(success=False, output="", error=f"Invalid pattern: {exc}")

        if not matched:
            return ToolResult(
                success=True,
                output=f"No files matched pattern '{pattern}'",
            )

        lines = "\n".join(matched)
        note = (
            f"\n[results capped at {_MAX_RESULTS}; refine pattern or path to see more]"
            if len(matched) == _MAX_RESULTS
            else ""
        )
        return ToolResult(
            success=True,
            output=f"[{len(matched)} file(s) matching '{pattern}']\n{lines}{note}",
        )
