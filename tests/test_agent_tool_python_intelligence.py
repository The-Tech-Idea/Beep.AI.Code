"""Tests for Python/Jedi-backed workspace-intelligence tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from beep.agent.tools.python_intelligence import (
    PythonDefinitionTool,
    PythonHoverTool,
    PythonJediAdapter,
    PythonRenameTool,
    PythonReferencesTool,
    PythonWorkspaceSymbolsTool,
)
from beep.runtime.builtin_workspace_intelligence import PythonJediWorkspaceIntelligencePlugin


@dataclass(frozen=True)
class _FakeName:
    name: str
    type: str
    description: str
    module_path: Path | None
    line: int | None
    column: int | None
    raw_docstring: str = ""

    def docstring(self) -> str:
        return self.raw_docstring


class _FakeJediAPI:
    def __init__(
        self,
        *,
        inferred: list[_FakeName] | None = None,
        definitions: list[_FakeName] | None = None,
        references: list[_FakeName] | None = None,
        search_results: list[_FakeName] | None = None,
        file_renames: list[tuple[Path, Path]] | None = None,
    ) -> None:
        self.inferred = list(inferred or [])
        self.definitions = list(definitions or [])
        self.references = list(references or [])
        self.search_results = list(search_results or [])
        self.file_renames = list(file_renames or [])
        self.project_paths: list[str] = []
        self.script_paths: list[str] = []
        self.apply_calls = 0
        self.calls: dict[str, list[dict[str, object]]] = {
            "infer": [],
            "goto": [],
            "references": [],
            "rename": [],
            "search": [],
        }

    def loader(self):
        api = self

        class FakeProject:
            def __init__(self, path: str) -> None:
                api.project_paths.append(path)

            def search(self, query: str, *, all_scopes: bool):
                api.calls["search"].append({"query": query, "all_scopes": all_scopes})
                return list(api.search_results)

        class FakeScript:
            def __init__(self, *, path: str, project: object) -> None:
                del project
                api.script_paths.append(path)

            def infer(self, *, line: int, column: int):
                api.calls["infer"].append({"line": line, "column": column})
                return list(api.inferred)

            def goto(
                self,
                *,
                line: int,
                column: int,
                follow_imports: bool,
                follow_builtin_imports: bool,
            ):
                api.calls["goto"].append(
                    {
                        "line": line,
                        "column": column,
                        "follow_imports": follow_imports,
                        "follow_builtin_imports": follow_builtin_imports,
                    }
                )
                return list(api.definitions)

            def get_references(self, *, line: int, column: int, include_builtins: bool):
                api.calls["references"].append(
                    {
                        "line": line,
                        "column": column,
                        "include_builtins": include_builtins,
                    }
                )
                return list(api.references)

            def rename(self, *, line: int, column: int, new_name: str):
                api.calls["rename"].append(
                    {
                        "line": line,
                        "column": column,
                        "new_name": new_name,
                    }
                )

                class FakeRefactoring:
                    def apply(self) -> None:
                        api.apply_calls += 1

                    def get_renames(self):
                        return list(api.file_renames)

                return FakeRefactoring()

        return FakeProject, FakeScript


@pytest.mark.asyncio
async def test_python_hover_tool_formats_symbol_details(tmp_path: Path) -> None:
    python_file = tmp_path / "pkg" / "sample.py"
    python_file.parent.mkdir(parents=True, exist_ok=True)
    python_file.write_text("def greet(name: str) -> str:\n    return name\n", encoding="utf-8")
    api = _FakeJediAPI(
        inferred=[
            _FakeName(
                name="greet",
                type="function",
                description="def greet(name: str) -> str",
                module_path=python_file,
                line=1,
                column=0,
                raw_docstring="Return the provided name.",
            )
        ]
    )
    adapter = PythonJediAdapter(
        workspace_root=tmp_path,
        api_loader=api.loader,
        python_file_counter=lambda _root: 1,
    )

    result = await PythonHoverTool(adapter).execute(file_path="pkg/sample.py", line=1, column=1)

    assert result.success
    assert "Hover for pkg/sample.py:1:1" in result.output
    assert "greet [function] - pkg/sample.py:1:1" in result.output
    assert "Return the provided name." in result.output
    assert api.calls["infer"] == [{"line": 1, "column": 0}]


@pytest.mark.asyncio
async def test_python_definition_tool_formats_locations(tmp_path: Path) -> None:
    python_file = tmp_path / "pkg" / "sample.py"
    python_file.parent.mkdir(parents=True, exist_ok=True)
    python_file.write_text("helper = 1\nvalue = helper\n", encoding="utf-8")
    api = _FakeJediAPI(
        definitions=[
            _FakeName(
                name="helper",
                type="statement",
                description="helper = 1",
                module_path=python_file,
                line=1,
                column=0,
            )
        ]
    )
    adapter = PythonJediAdapter(
        workspace_root=tmp_path,
        api_loader=api.loader,
        python_file_counter=lambda _root: 1,
    )

    result = await PythonDefinitionTool(adapter).execute(file_path=str(python_file), line=2, column=9)

    assert result.success
    assert f"Definitions for {python_file}:2:9" in result.output
    assert "helper [statement] - pkg/sample.py:1:1" in result.output
    assert api.calls["goto"] == [
        {
            "line": 2,
            "column": 8,
            "follow_imports": True,
            "follow_builtin_imports": False,
        }
    ]


@pytest.mark.asyncio
async def test_python_references_tool_formats_reference_locations(tmp_path: Path) -> None:
    python_file = tmp_path / "pkg" / "sample.py"
    python_file.parent.mkdir(parents=True, exist_ok=True)
    python_file.write_text("helper = 1\nvalue = helper\nprint(helper)\n", encoding="utf-8")
    api = _FakeJediAPI(
        references=[
            _FakeName(
                name="helper",
                type="statement",
                description="helper = 1",
                module_path=python_file,
                line=1,
                column=0,
            ),
            _FakeName(
                name="helper",
                type="statement",
                description="value = helper",
                module_path=python_file,
                line=2,
                column=8,
            ),
        ]
    )
    adapter = PythonJediAdapter(
        workspace_root=tmp_path,
        api_loader=api.loader,
        python_file_counter=lambda _root: 1,
    )

    result = await PythonReferencesTool(adapter).execute(file_path="pkg/sample.py", line=2, column=9)

    assert result.success
    assert "References for pkg/sample.py:2:9" in result.output
    assert "pkg/sample.py:1:1" in result.output
    assert "pkg/sample.py:2:9" in result.output
    assert api.calls["references"] == [{"line": 2, "column": 8, "include_builtins": False}]


@pytest.mark.asyncio
async def test_python_workspace_symbols_tool_formats_project_search_results(tmp_path: Path) -> None:
    python_file = tmp_path / "pkg" / "sample.py"
    python_file.parent.mkdir(parents=True, exist_ok=True)
    python_file.write_text("def helper():\n    return 1\n", encoding="utf-8")
    api = _FakeJediAPI(
        search_results=[
            _FakeName(
                name="helper",
                type="function",
                description="def helper()",
                module_path=python_file,
                line=1,
                column=0,
                raw_docstring="Return a constant.",
            )
        ]
    )
    adapter = PythonJediAdapter(
        workspace_root=tmp_path,
        api_loader=api.loader,
        python_file_counter=lambda _root: 1,
    )

    result = await PythonWorkspaceSymbolsTool(adapter).execute(query="helper", top_k=5)

    assert result.success
    assert "Python workspace symbols for query: 'helper'" in result.output
    assert "helper [function] - pkg/sample.py:1:1" in result.output
    assert "Return a constant." in result.output
    assert api.calls["search"] == [{"query": "helper", "all_scopes": True}]


@pytest.mark.asyncio
async def test_python_rename_tool_applies_refactoring_and_reports_changed_files(tmp_path: Path) -> None:
    source_file = tmp_path / "pkg" / "sample.py"
    other_file = tmp_path / "pkg" / "other.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("helper = 1\nvalue = helper\n", encoding="utf-8")
    other_file.write_text("from pkg.sample import helper\nprint(helper)\n", encoding="utf-8")
    api = _FakeJediAPI(
        references=[
            _FakeName(
                name="helper",
                type="statement",
                description="helper = 1",
                module_path=source_file,
                line=1,
                column=0,
            ),
            _FakeName(
                name="helper",
                type="statement",
                description="print(helper)",
                module_path=other_file,
                line=2,
                column=6,
            ),
        ]
    )
    adapter = PythonJediAdapter(
        workspace_root=tmp_path,
        api_loader=api.loader,
        python_file_counter=lambda _root: 2,
    )

    result = await PythonRenameTool(adapter).execute(
        file_path="pkg/sample.py",
        line=2,
        column=9,
        new_name="renamed_helper",
    )

    assert result.success
    assert "Renamed Python symbol at pkg/sample.py:2:9" in result.output
    assert "New name: renamed_helper" in result.output
    assert "1. pkg/other.py" in result.output
    assert "2. pkg/sample.py" in result.output
    assert api.calls["references"] == [{"line": 2, "column": 8, "include_builtins": False}]
    assert api.calls["rename"] == [{"line": 2, "column": 8, "new_name": "renamed_helper"}]
    assert api.apply_calls == 1


def test_python_jedi_adapter_reports_missing_python_files_without_loading_jedi(tmp_path: Path) -> None:
    adapter = PythonJediAdapter(
        workspace_root=tmp_path,
        api_loader=lambda: (_ for _ in ()).throw(AssertionError("loader should not run")),
    )

    report = adapter.availability_report()

    assert report["available"] is False
    assert report["python_files"] == 0
    assert "No Python files detected" in str(report["error"])


def test_python_workspace_plugin_exposes_lsp_capabilities_tools_and_status(tmp_path: Path) -> None:
    python_file = tmp_path / "pkg" / "sample.py"
    python_file.parent.mkdir(parents=True, exist_ok=True)
    python_file.write_text("helper = 1\n", encoding="utf-8")
    api = _FakeJediAPI(
        inferred=[
            _FakeName(
                name="helper",
                type="statement",
                description="helper = 1",
                module_path=python_file,
                line=1,
                column=0,
            )
        ]
    )
    plugin = PythonJediWorkspaceIntelligencePlugin(
        adapter_factory=lambda root: PythonJediAdapter(
            workspace_root=root,
            api_loader=api.loader,
            python_file_counter=lambda _root: 1,
        )
    )

    capabilities = plugin.capabilities(workspace_root=tmp_path)
    tools = plugin.get_tools_for_workspace(tmp_path)
    report = plugin.get_status_report(tmp_path)

    assert capabilities.semantic_search.semantic_search.exists is False
    assert capabilities.lsp.hover.exists is True
    assert capabilities.lsp.definition.exists is True
    assert capabilities.lsp.references.exists is True
    assert capabilities.lsp.rename.exists is True
    assert capabilities.lsp.workspace_symbols.exists is True
    assert {tool.name for tool in tools} == {
        "python_hover",
        "python_definition",
        "python_references",
        "python_rename",
        "python_workspace_symbols",
    }
    assert {tool.name: tool.read_only_safe for tool in tools} == {
        "python_hover": True,
        "python_definition": True,
        "python_references": True,
        "python_rename": False,
        "python_workspace_symbols": True,
    }
    assert report is not None
    assert report.title == "Workspace Intelligence: Python/Jedi"
    assert ("Python Files", "1") in {(row.label, row.value) for row in report.rows}
    assert ("Supported Operations", "hover, definition, references, rename, workspace_symbols") in {
        (row.label, row.value) for row in report.rows
    }