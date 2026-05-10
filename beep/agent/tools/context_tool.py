"""Batch file reader tool for agent context loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult

_MAX_LINES_PER_FILE = 300
_MAX_FILES = 20
_SEPARATOR = "=" * 60


class ContextTool(BaseTool):
    """Read multiple files in a single call for context loading.

    Use this instead of calling file_read N times when you need to load
    several files at once (e.g. before editing, before reviewing).

    Each file is returned under a ``## path`` header, truncated to
    300 lines.  If a file exceeds 300 lines the header reports its
    total line count so you can follow up with file_read start_line/end_line
    for the remaining pages.

    Accepts up to 20 paths per call.  Paths may be absolute or
    workspace-relative.
    """

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root.resolve() if workspace_root else None

    def _resolve(self, raw: str) -> Path:
        p = Path(raw)
        if p.is_absolute():
            return p
        if self._workspace_root:
            return (self._workspace_root / p).resolve()
        return p.resolve()

    def _is_outside_workspace(self, path: Path) -> bool:
        return bool(
            self._workspace_root
            and self._workspace_root not in path.parents
            and path != self._workspace_root
        )

    @property
    def name(self) -> str:
        return "read_files"

    @property
    def description(self) -> str:
        return (
            "Read multiple files at once and return their contents concatenated. "
            "Each file is prefixed with a '## <path>' header. "
            "Files are truncated at 300 lines — the header reports total_lines "
            "so you can page with file_read if needed. "
            "Accepts workspace-relative or absolute paths. "
            "Preferred over calling file_read repeatedly when loading context."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of file paths to read (workspace-relative or absolute). "
                    f"Maximum {_MAX_FILES} paths per call."
                ),
            }
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        paths_raw: list[str] = kwargs.get("paths", [])
        if not paths_raw:
            return ToolResult(success=False, output="", error="No paths provided.")

        if len(paths_raw) > _MAX_FILES:
            return ToolResult(
                success=False,
                output="",
                error=f"Too many paths: {len(paths_raw)} (max {_MAX_FILES}). Split into smaller batches.",
            )

        sections: list[str] = []
        errors: list[str] = []

        for raw in paths_raw:
            path = self._resolve(raw)
            if self._is_outside_workspace(path):
                errors.append(f"  {raw}: outside workspace")
                continue
            if not path.exists():
                errors.append(f"  {raw}: not found")
                continue
            if not path.is_file():
                errors.append(f"  {raw}: not a file")
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                errors.append(f"  {raw}: read error — {exc}")
                continue

            all_lines = text.splitlines(keepends=True)
            total = len(all_lines)
            truncated = total > _MAX_LINES_PER_FILE
            shown_lines = all_lines[:_MAX_LINES_PER_FILE]
            content = "".join(shown_lines)

            # Display relative path when possible
            try:
                display = str(path.relative_to(self._workspace_root)) if self._workspace_root else str(path)
            except ValueError:
                display = str(path)

            if truncated:
                header = (
                    f"## {display}  "
                    f"[total_lines: {total}  showing: 1-{_MAX_LINES_PER_FILE}  "
                    f"(truncated — use file_read start_line/end_line for more)]"
                )
            else:
                header = f"## {display}  [total_lines: {total}]"

            sections.append(f"{header}\n{content}")

        if not sections and errors:
            return ToolResult(
                success=False,
                output="",
                error="All paths failed:\n" + "\n".join(errors),
            )

        output_parts = [f"\n{_SEPARATOR}\n".join(sections)]
        if errors:
            output_parts.append(f"\n{_SEPARATOR}\nWarnings (some paths skipped):\n" + "\n".join(errors))

        return ToolResult(success=True, output="".join(output_parts))
