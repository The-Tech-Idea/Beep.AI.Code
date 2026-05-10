"""Tool wrappers for Jedi-backed Python code intelligence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.agent.tools.python_intelligence_core import (
    PythonJediAdapter,
    _format_rename_result,
    _format_symbol_records,
)


class PythonHoverTool(BaseTool):
    def __init__(self, adapter: PythonJediAdapter) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "python_hover"

    @property
    def description(self) -> str:
        return "Inspect a Python symbol at a file location using Jedi hover-style inference."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Python file path inside the workspace.",
            },
            "line": {"type": "integer", "description": "1-based line number for the symbol."},
            "column": {
                "type": "integer",
                "description": "1-based column number for the symbol (default 1).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["column"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            record = self._adapter.hover(
                file_path=str(kwargs.get("file_path") or ""),
                line=kwargs.get("line"),
                column=kwargs.get("column"),
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)
        output = _format_symbol_records(
            f"Hover for {kwargs.get('file_path')}:{kwargs.get('line')}:{kwargs.get('column') or 1}",
            [record],
        )
        return ToolResult(success=True, output=output)


class PythonDefinitionTool(BaseTool):
    def __init__(self, adapter: PythonJediAdapter) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "python_definition"

    @property
    def description(self) -> str:
        return "Resolve Python symbol definitions at a file location using Jedi."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Python file path inside the workspace.",
            },
            "line": {"type": "integer", "description": "1-based line number for the symbol."},
            "column": {
                "type": "integer",
                "description": "1-based column number for the symbol (default 1).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["column"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            records = self._adapter.definitions(
                file_path=str(kwargs.get("file_path") or ""),
                line=kwargs.get("line"),
                column=kwargs.get("column"),
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)
        output = _format_symbol_records(
            f"Definitions for {kwargs.get('file_path')}:{kwargs.get('line')}:{kwargs.get('column') or 1}",
            records,
        )
        return ToolResult(success=True, output=output)


class PythonReferencesTool(BaseTool):
    def __init__(self, adapter: PythonJediAdapter) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "python_references"

    @property
    def description(self) -> str:
        return "Find Python symbol references at a file location using Jedi."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Python file path inside the workspace.",
            },
            "line": {"type": "integer", "description": "1-based line number for the symbol."},
            "column": {
                "type": "integer",
                "description": "1-based column number for the symbol (default 1).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["column"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            records = self._adapter.references(
                file_path=str(kwargs.get("file_path") or ""),
                line=kwargs.get("line"),
                column=kwargs.get("column"),
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)
        output = _format_symbol_records(
            f"References for {kwargs.get('file_path')}:{kwargs.get('line')}:{kwargs.get('column') or 1}",
            records,
        )
        return ToolResult(success=True, output=output)


class PythonWorkspaceSymbolsTool(BaseTool):
    def __init__(self, adapter: PythonJediAdapter) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "python_workspace_symbols"

    @property
    def description(self) -> str:
        return "Search Python workspace symbols by name using Jedi project search."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "Symbol name or partial name to search for.",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of symbol matches to return (default 10).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["top_k"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            records = self._adapter.workspace_symbols(
                query=str(kwargs.get("query") or ""),
                top_k=kwargs.get("top_k"),
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)
        output = _format_symbol_records(
            f"Python workspace symbols for query: {kwargs.get('query')!r}",
            records,
        )
        return ToolResult(success=True, output=output)


class PythonRenameTool(BaseTool):
    def __init__(self, adapter: PythonJediAdapter) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "python_rename"

    @property
    def description(self) -> str:
        return "Rename a Python symbol across the workspace using Jedi refactoring support."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Python file path inside the workspace.",
            },
            "line": {
                "type": "integer",
                "description": "1-based line number for the target symbol.",
            },
            "column": {
                "type": "integer",
                "description": "1-based column number for the target symbol (default 1).",
            },
            "new_name": {
                "type": "string",
                "description": "New Python identifier to apply to the symbol.",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["column"]

    @property
    def category(self) -> str:
        return "file"

    @property
    def read_only_safe(self) -> bool:
        return False

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = self._adapter.rename(
                file_path=str(kwargs.get("file_path") or ""),
                line=kwargs.get("line"),
                column=kwargs.get("column"),
                new_name=kwargs.get("new_name"),
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)
        output = _format_rename_result(
            f"Renamed Python symbol at {kwargs.get('file_path')}:{kwargs.get('line')}:{kwargs.get('column') or 1}",
            result,
        )
        return ToolResult(success=True, output=output)


def build_python_intelligence_tools(
    *,
    workspace_root: Path,
    adapter: PythonJediAdapter | None = None,
) -> tuple[BaseTool, ...]:
    if adapter is None:
        from beep.app_service import get_app_service

        shared_adapter = get_app_service().python_jedi(workspace_root)
    else:
        shared_adapter = adapter
    return (
        PythonHoverTool(shared_adapter),
        PythonDefinitionTool(shared_adapter),
        PythonReferencesTool(shared_adapter),
        PythonRenameTool(shared_adapter),
        PythonWorkspaceSymbolsTool(shared_adapter),
    )
