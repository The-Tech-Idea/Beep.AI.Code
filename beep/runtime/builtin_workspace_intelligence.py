"""Built-in workspace-intelligence plugins."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from beep.agent.tools.base import BaseTool
from beep.plugins.registry import PluginInfo, WorkspaceIntelligencePlugin
from beep.runtime.capabilities import CapabilityFlag
from beep.runtime.workspace_intelligence import (
    LSPCapabilities,
    SemanticSearchCapabilities,
    WorkspaceIntelligenceCapabilities,
    WorkspaceIntelligenceStatusReport,
    WorkspaceIntelligenceStatusRow,
    build_semantic_search_status_report,
    build_workspace_intelligence_capabilities,
)

if TYPE_CHECKING:
    from beep.agent.tools.python_intelligence import PythonJediAdapter
    from beep.agent.tools.semantic_search import SembleIndexAdapter


def _disabled_semantic_search_capabilities(note: str) -> SemanticSearchCapabilities:
    return SemanticSearchCapabilities(
        semantic_search=CapabilityFlag(False, note),
        find_related=CapabilityFlag(False, note),
        local_indexing=CapabilityFlag(False, note),
        remote_git_indexing=CapabilityFlag(False, note),
        hybrid_mode=CapabilityFlag(False, note),
        semantic_mode=CapabilityFlag(False, note),
        bm25_mode=CapabilityFlag(False, note),
        language_filters=CapabilityFlag(False, note),
        path_filters=CapabilityFlag(False, note),
        index_stats=CapabilityFlag(False, note),
    )


def _build_python_jedi_capabilities(report: dict[str, object]) -> WorkspaceIntelligenceCapabilities:
    available = bool(report.get("available"))
    python_files = int(report.get("python_files", 0) or 0)
    if available:
        lsp_note = f"Python code intelligence available through Jedi ({python_files} Python files detected)."
    else:
        lsp_note = str(report.get("error") or "Python code intelligence is unavailable.")
    semantic_note = "This plugin does not provide semantic search; use Semble or another semantic-search plugin."
    return WorkspaceIntelligenceCapabilities(
        semantic_search=_disabled_semantic_search_capabilities(semantic_note),
        lsp=LSPCapabilities(
            diagnostics=CapabilityFlag(False, "Jedi does not provide diagnostics."),
            hover=CapabilityFlag(available, lsp_note),
            definition=CapabilityFlag(available, lsp_note),
            references=CapabilityFlag(available, lsp_note),
            rename=CapabilityFlag(available, lsp_note),
            workspace_symbols=CapabilityFlag(available, lsp_note),
            code_actions=CapabilityFlag(False, "Jedi does not provide code actions."),
            formatting=CapabilityFlag(
                False, "Formatting is outside the built-in Python/Jedi plugin."
            ),
        ),
    )


def _build_python_jedi_status_report(
    report: dict[str, object],
) -> WorkspaceIntelligenceStatusReport:
    return WorkspaceIntelligenceStatusReport(
        title="Workspace Intelligence: Python/Jedi",
        rows=(
            WorkspaceIntelligenceStatusRow("Backend", "Jedi"),
            WorkspaceIntelligenceStatusRow("Available", "Yes" if report.get("available") else "No"),
            WorkspaceIntelligenceStatusRow(
                "Workspace", str(report.get("workspace_root") or "None")
            ),
            WorkspaceIntelligenceStatusRow("Python Files", str(report.get("python_files", 0) or 0)),
            WorkspaceIntelligenceStatusRow(
                "Supported Operations", "hover, definition, references, rename, workspace_symbols"
            ),
            WorkspaceIntelligenceStatusRow("Last Error", str(report.get("error") or "None")),
        ),
    )


class SembleWorkspaceIntelligencePlugin(WorkspaceIntelligencePlugin):
    """Built-in workspace-intelligence plugin backed by Semble."""

    info = PluginInfo(
        name="builtin-semble-workspace-intelligence",
        version="1.0.0",
        description="Built-in Semble semantic search support for workspace intelligence.",
    )

    def __init__(self) -> None:
        self._adapters: dict[Path, "SembleIndexAdapter"] = {}

    def activate(self) -> None:
        return None

    def _get_adapter(self, workspace_root: Path) -> "SembleIndexAdapter":
        from beep.app_service import get_app_service

        return get_app_service().semble_index(workspace_root)

    def capabilities(self, *, workspace_root: Path) -> WorkspaceIntelligenceCapabilities:
        adapter = self._get_adapter(workspace_root)
        return build_workspace_intelligence_capabilities(adapter.availability_report())

    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]:
        from beep.agent.tools.semantic_search import build_semble_tools

        adapter = self._get_adapter(workspace_root)
        if not adapter.availability_report().get("available"):
            return []
        return list(build_semble_tools(workspace_root=workspace_root, adapter=adapter))

    def get_semantic_search_adapter(self, workspace_root: Path) -> "SembleIndexAdapter" | None:
        return self._get_adapter(workspace_root)

    def get_status_report(self, workspace_root: Path) -> WorkspaceIntelligenceStatusReport | None:
        return build_semantic_search_status_report(
            self._get_adapter(workspace_root).availability_report(),
            title="Workspace Intelligence: Semble",
        )


class PythonJediWorkspaceIntelligencePlugin(WorkspaceIntelligencePlugin):
    """Built-in Python code-intelligence plugin backed by Jedi."""

    info = PluginInfo(
        name="builtin-python-jedi-workspace-intelligence",
        version="1.0.0",
        description="Built-in Python hover, definition, reference, rename, and workspace-symbol support for workspace intelligence.",
    )

    def __init__(
        self,
        adapter_factory: Callable[[Path], "PythonJediAdapter"] | None = None,
    ) -> None:
        self._adapter_factory = adapter_factory
        self._adapters: dict[Path, "PythonJediAdapter"] = {}

    def activate(self) -> None:
        return None

    def _get_adapter(self, workspace_root: Path) -> "PythonJediAdapter":
        if self._adapter_factory is not None:
            return self._adapter_factory(workspace_root)
        from beep.app_service import get_app_service

        return get_app_service().python_jedi(workspace_root)

    def capabilities(self, *, workspace_root: Path) -> WorkspaceIntelligenceCapabilities:
        return _build_python_jedi_capabilities(
            self._get_adapter(workspace_root).availability_report()
        )

    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]:
        from beep.agent.tools.python_intelligence import build_python_intelligence_tools

        adapter = self._get_adapter(workspace_root)
        if not adapter.availability_report().get("available"):
            return []
        return list(build_python_intelligence_tools(workspace_root=workspace_root, adapter=adapter))

    def get_status_report(self, workspace_root: Path) -> WorkspaceIntelligenceStatusReport | None:
        return _build_python_jedi_status_report(
            self._get_adapter(workspace_root).availability_report()
        )


class CSharpWorkspaceIntelligencePlugin(WorkspaceIntelligencePlugin):
    """Built-in C# code-intelligence plugin backed by Roslyn analysis."""

    info = PluginInfo(
        name="builtin-csharp-workspace-intelligence",
        version="1.0.0",
        description="Built-in C# symbols, diagnostics, and dependency analysis for workspace intelligence.",
    )

    def activate(self) -> None:
        return None

    def capabilities(self, *, workspace_root: Path) -> WorkspaceIntelligenceCapabilities:
        from beep.languages.csharp import CSharpAdapter

        adapter = CSharpAdapter()
        available = adapter.detect(str(workspace_root))
        note = (
            "C# code intelligence available via Roslyn analysis."
            if available
            else "No C# solution detected in workspace."
        )
        return WorkspaceIntelligenceCapabilities(
            semantic_search=_disabled_semantic_search_capabilities(note),
            lsp=LSPCapabilities(
                diagnostics=CapabilityFlag(
                    available, "Roslyn diagnostics available." if available else note
                ),
                hover=CapabilityFlag(False, "Not supported yet."),
                definition=CapabilityFlag(False, "Not supported yet."),
                references=CapabilityFlag(False, "Not supported yet."),
                rename=CapabilityFlag(False, "Not supported yet."),
                workspace_symbols=CapabilityFlag(
                    available, "Roslyn symbol extraction available." if available else note
                ),
                code_actions=CapabilityFlag(False, "Not supported yet."),
                formatting=CapabilityFlag(False, "Use dotnet format CLI."),
            ),
        )

    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]:
        from beep.agent.tools.csharp_intelligence_tools import build_csharp_intelligence_tools

        return list(build_csharp_intelligence_tools(workspace_root=workspace_root))

    def get_status_report(self, workspace_root: Path) -> WorkspaceIntelligenceStatusReport | None:
        from beep.languages.csharp import CSharpAdapter

        adapter = CSharpAdapter()
        available = adapter.detect(str(workspace_root))
        return WorkspaceIntelligenceStatusReport(
            title="Workspace Intelligence: C#/Roslyn",
            rows=(
                WorkspaceIntelligenceStatusRow("Backend", "Roslyn Analysis"),
                WorkspaceIntelligenceStatusRow("Available", "Yes" if available else "No"),
                WorkspaceIntelligenceStatusRow("Workspace", str(workspace_root)),
                WorkspaceIntelligenceStatusRow(
                    "Supported Operations", "symbols, diagnostics, dependencies"
                ),
            ),
        )


class JavaScriptWorkspaceIntelligencePlugin(WorkspaceIntelligencePlugin):
    """Built-in JavaScript code-intelligence plugin using tree-sitter parsing."""

    info = PluginInfo(
        name="builtin-javascript-workspace-intelligence",
        version="1.0.0",
        description="Built-in JavaScript symbol search and definition lookup via tree-sitter parsing.",
    )

    def activate(self) -> None:
        return None

    def capabilities(self, *, workspace_root: Path) -> WorkspaceIntelligenceCapabilities:
        from beep.languages.javascript import JavaScriptAdapter

        adapter = JavaScriptAdapter()
        available = adapter.detect(str(workspace_root))
        note = (
            "JavaScript code intelligence available via tree-sitter parsing."
            if available
            else "No JavaScript project detected."
        )
        return WorkspaceIntelligenceCapabilities(
            semantic_search=_disabled_semantic_search_capabilities(note),
            lsp=LSPCapabilities(
                diagnostics=CapabilityFlag(False, "Not supported yet."),
                hover=CapabilityFlag(False, "Not supported yet."),
                definition=CapabilityFlag(
                    available, "Tree-sitter definition lookup available." if available else note
                ),
                references=CapabilityFlag(False, "Not supported yet."),
                rename=CapabilityFlag(False, "Not supported yet."),
                workspace_symbols=CapabilityFlag(
                    available, "Tree-sitter symbol search available." if available else note
                ),
                code_actions=CapabilityFlag(False, "Not supported yet."),
                formatting=CapabilityFlag(False, "Use eslint or biome CLI."),
            ),
        )

    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]:
        from beep.agent.tools.javascript_intelligence_tools import (
            build_javascript_intelligence_tools,
        )

        return list(build_javascript_intelligence_tools(workspace_root=workspace_root))

    def get_status_report(self, workspace_root: Path) -> WorkspaceIntelligenceStatusReport | None:
        from beep.languages.javascript import JavaScriptAdapter

        adapter = JavaScriptAdapter()
        available = adapter.detect(str(workspace_root))
        return WorkspaceIntelligenceStatusReport(
            title="Workspace Intelligence: JavaScript/tree-sitter",
            rows=(
                WorkspaceIntelligenceStatusRow("Backend", "Tree-Sitter"),
                WorkspaceIntelligenceStatusRow("Available", "Yes" if available else "No"),
                WorkspaceIntelligenceStatusRow("Workspace", str(workspace_root)),
                WorkspaceIntelligenceStatusRow("Supported Operations", "symbols, definitions"),
            ),
        )


class TypeScriptWorkspaceIntelligencePlugin(WorkspaceIntelligencePlugin):
    """Built-in TypeScript code-intelligence plugin using tree-sitter parsing."""

    info = PluginInfo(
        name="builtin-typescript-workspace-intelligence",
        version="1.0.0",
        description="Built-in TypeScript symbol search and definition lookup via tree-sitter parsing.",
    )

    def activate(self) -> None:
        return None

    def capabilities(self, *, workspace_root: Path) -> WorkspaceIntelligenceCapabilities:
        from beep.languages.typescript import TypeScriptAdapter

        adapter = TypeScriptAdapter()
        available = adapter.detect(str(workspace_root))
        note = (
            "TypeScript code intelligence available via tree-sitter parsing."
            if available
            else "No TypeScript project detected."
        )
        return WorkspaceIntelligenceCapabilities(
            semantic_search=_disabled_semantic_search_capabilities(note),
            lsp=LSPCapabilities(
                diagnostics=CapabilityFlag(False, "Not supported yet."),
                hover=CapabilityFlag(False, "Not supported yet."),
                definition=CapabilityFlag(
                    available, "Tree-sitter definition lookup available." if available else note
                ),
                references=CapabilityFlag(False, "Not supported yet."),
                rename=CapabilityFlag(False, "Not supported yet."),
                workspace_symbols=CapabilityFlag(
                    available, "Tree-sitter symbol search available." if available else note
                ),
                code_actions=CapabilityFlag(False, "Not supported yet."),
                formatting=CapabilityFlag(False, "Use eslint or biome CLI."),
            ),
        )

    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]:
        from beep.agent.tools.typescript_intelligence_tools import (
            build_typescript_intelligence_tools,
        )

        return list(build_typescript_intelligence_tools(workspace_root=workspace_root))

    def get_status_report(self, workspace_root: Path) -> WorkspaceIntelligenceStatusReport | None:
        from beep.languages.typescript import TypeScriptAdapter

        adapter = TypeScriptAdapter()
        available = adapter.detect(str(workspace_root))
        return WorkspaceIntelligenceStatusReport(
            title="Workspace Intelligence: TypeScript/tree-sitter",
            rows=(
                WorkspaceIntelligenceStatusRow("Backend", "Tree-Sitter"),
                WorkspaceIntelligenceStatusRow("Available", "Yes" if available else "No"),
                WorkspaceIntelligenceStatusRow("Workspace", str(workspace_root)),
                WorkspaceIntelligenceStatusRow("Supported Operations", "symbols, definitions"),
            ),
        )
