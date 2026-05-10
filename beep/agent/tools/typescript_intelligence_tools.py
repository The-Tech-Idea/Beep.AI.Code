"""TypeScript code intelligence tools using tree-sitter parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.codeindex.tree_sitter_parser import TreeSitterParser
from beep.codeindex.symbols import SymbolKind
from beep.languages._shared import relative_path


class TypeScriptSymbolsTool(BaseTool):
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        from beep.app_service import get_app_service

        self._parser = get_app_service().tree_sitter_parser

    @property
    def name(self) -> str:
        return "typescript_symbols"

    @property
    def description(self) -> str:
        return "Search TypeScript/TSX symbols (functions, classes, interfaces, imports) using tree-sitter parsing."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "Symbol name or partial name to search for.",
            },
            "kind": {
                "type": "string",
                "description": "Filter by symbol kind: function, class, interface, import (optional).",
            },
            "top_k": {"type": "integer", "description": "Maximum number of results (default 20)."},
        }

    @property
    def optional_params(self) -> list[str]:
        return ["kind", "top_k"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = (kwargs.get("query") or "").lower()
        if not query:
            return ToolResult(success=False, output="", error="query is required", is_error=True)

        try:
            symbols = self._parser.parse_directory(
                str(self._workspace_root),
                extensions=[".ts", ".tsx"],
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)

        kind_filter = (kwargs.get("kind") or "").lower()
        top_k = min(int(kwargs.get("top_k") or 20), 100)

        filtered = []
        for sym in symbols:
            if query not in sym.name.lower():
                continue
            if kind_filter:
                kind_map = {
                    "function": SymbolKind.FUNCTION,
                    "class": SymbolKind.CLASS,
                    "interface": SymbolKind.INTERFACE,
                    "import": SymbolKind.IMPORT,
                }
                expected = kind_map.get(kind_filter)
                if expected and sym.kind != expected:
                    continue
            filtered.append(sym)

        output_lines = [f"TypeScript symbols for query: {query!r} (found: {len(filtered)})"]
        for sym in filtered[:top_k]:
            rel_path = relative_path(self._workspace_root, Path(sym.file_path))
            output_lines.append(f"  [{sym.kind.value}] {sym.name} ({rel_path}:{sym.start_line})")
            if sym.signature:
                output_lines.append(f"    {sym.signature}")

        if len(filtered) > top_k:
            output_lines.append(f"  ... and {len(filtered) - top_k} more symbols")

        return ToolResult(success=True, output="\n".join(output_lines))


class TypeScriptDefinitionsTool(BaseTool):
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        from beep.app_service import get_app_service

        self._parser = get_app_service().tree_sitter_parser

    @property
    def name(self) -> str:
        return "typescript_definitions"

    @property
    def description(self) -> str:
        return "Find TypeScript function/class/interface definitions in a specific file using tree-sitter parsing."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "TypeScript file path inside the workspace.",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return []

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path", "")
        if not file_path:
            return ToolResult(
                success=False, output="", error="file_path is required", is_error=True
            )

        try:
            symbols = self._parser.parse_file(str(file_path))
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)

        defs = [
            s
            for s in symbols
            if s.kind
            in (SymbolKind.FUNCTION, SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.METHOD)
        ]
        output_lines = [f"TypeScript definitions in {file_path} (found: {len(defs)})"]
        for sym in defs:
            output_lines.append(f"  [{sym.kind.value}] {sym.name} (line {sym.start_line})")
            if sym.signature:
                output_lines.append(f"    {sym.signature}")

        return ToolResult(success=True, output="\n".join(output_lines))


def build_typescript_intelligence_tools(
    *,
    workspace_root: Path,
) -> tuple[BaseTool, ...]:
    return (
        TypeScriptSymbolsTool(workspace_root),
        TypeScriptDefinitionsTool(workspace_root),
    )
