"""C# code intelligence tools using Roslyn analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.languages.csharp import CSharpAdapter


class CSharpSymbolsTool(BaseTool):
    def __init__(self, adapter: CSharpAdapter, workspace_root: Path) -> None:
        self._adapter = adapter
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "csharp_symbols"

    @property
    def description(self) -> str:
        return "Extract C# symbols (classes, methods, properties) from the solution using Roslyn."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "filter": {
                "type": "string",
                "description": "Optional symbol name filter (partial match).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["filter"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = self._adapter.analyze_symbols(str(self._workspace_root))
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)

        if not result.get("ok"):
            return ToolResult(
                success=False, output="", error=result.get("error", "Unknown error"), is_error=True
            )

        symbols = result.get("symbols", [])
        filter_query = (kwargs.get("filter") or "").lower()
        if filter_query:
            symbols = [s for s in symbols if filter_query in s.get("name", "").lower()]

        output_lines = [f"C# symbols (total: {len(symbols)})"]
        for sym in symbols[:50]:
            sym_type = sym.get("kind", "unknown")
            sym_name = sym.get("name", "")
            sym_file = sym.get("file", "")
            sym_line = sym.get("line", "?")
            output_lines.append(f"  [{sym_type}] {sym_name} ({sym_file}:{sym_line})")

        if len(symbols) > 50:
            output_lines.append(f"  ... and {len(symbols) - 50} more symbols")

        return ToolResult(success=True, output="\n".join(output_lines))


class CSharpDiagnosticsTool(BaseTool):
    def __init__(self, adapter: CSharpAdapter, workspace_root: Path) -> None:
        self._adapter = adapter
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "csharp_diagnostics"

    @property
    def description(self) -> str:
        return "Get C# compiler diagnostics (errors/warnings) from the solution using Roslyn."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "severity": {
                "type": "string",
                "description": "Filter by severity: error, warning, info (default: all).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["severity"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = self._adapter.analyze_diagnostics(str(self._workspace_root))
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)

        severity_filter = (kwargs.get("severity") or "").lower()
        issues = result.issues
        if severity_filter:
            issues = [i for i in issues if severity_filter in i.severity.lower()]

        output_lines = [f"C# diagnostics (total: {len(issues)})"]
        for issue in issues[:50]:
            sev = issue.severity
            msg = issue.message
            file_path = issue.file_path
            line = issue.line if issue.line else "?"
            output_lines.append(f"  [{sev}] {file_path}:{line} - {msg}")

        if len(issues) > 50:
            output_lines.append(f"  ... and {len(issues) - 50} more diagnostics")

        return ToolResult(success=True, output="\n".join(output_lines))


class CSharpDependenciesTool(BaseTool):
    def __init__(self, adapter: CSharpAdapter, workspace_root: Path) -> None:
        self._adapter = adapter
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "csharp_dependencies"

    @property
    def description(self) -> str:
        return "Extract C# project dependencies using Roslyn."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "project": {"type": "string", "description": "Optional project name filter."},
        }

    @property
    def optional_params(self) -> list[str]:
        return ["project"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = self._adapter.analyze_dependencies(str(self._workspace_root))
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc), is_error=True)

        deps = result.dependencies
        project_filter = (kwargs.get("project") or "").lower()
        if project_filter:
            deps = [d for d in deps if project_filter in d.get("name", "").lower()]

        output_lines = [f"C# project dependencies (total: {len(deps)})"]
        for dep in deps[:50]:
            dep_name = dep.get("name", "")
            dep_type = dep.get("type", "unknown")
            output_lines.append(f"  [{dep_type}] {dep_name}")

        if len(deps) > 50:
            output_lines.append(f"  ... and {len(deps) - 50} more dependencies")

        return ToolResult(success=True, output="\n".join(output_lines))


def build_csharp_intelligence_tools(
    *,
    workspace_root: Path,
) -> tuple[BaseTool, ...]:
    adapter = CSharpAdapter()
    if not adapter.detect(str(workspace_root)):
        return ()
    return (
        CSharpSymbolsTool(adapter, workspace_root),
        CSharpDiagnosticsTool(adapter, workspace_root),
        CSharpDependenciesTool(adapter, workspace_root),
    )
