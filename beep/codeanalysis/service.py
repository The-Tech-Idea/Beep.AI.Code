"""Unified code analysis service."""

from __future__ import annotations

from pathlib import Path

from beep.codeanalysis.models import CodeAnalysisResult


class CodeAnalysisService:
    """Unified entry point for all code analyzers."""

    def __init__(self) -> None:
        self._tree_sitter = None
        self._complexity = None
        self._architecture = None
        self._semgrep = None
        self._python_libcst = None

    def _get_tree_sitter(self):
        if self._tree_sitter is None:
            from beep.codeanalysis.tree_sitter_analyzer import TreeSitterAnalyzer

            self._tree_sitter = TreeSitterAnalyzer()
        return self._tree_sitter

    def _get_complexity(self):
        if self._complexity is None:
            from beep.codeanalysis.complexity_analyzer import ComplexityAnalyzer

            self._complexity = ComplexityAnalyzer()
        return self._complexity

    def _get_architecture(self):
        if self._architecture is None:
            from beep.codeanalysis.architecture_analyzer import ArchitectureAnalyzer

            self._architecture = ArchitectureAnalyzer()
        return self._architecture

    def _get_semgrep(self):
        if self._semgrep is None:
            from beep.codeanalysis.semgrep_analyzer import SemgrepAnalyzer

            self._semgrep = SemgrepAnalyzer()
        return self._semgrep

    def _get_python_libcst(self):
        if self._python_libcst is None:
            from beep.codeanalysis.python_libcst_analyzer import LibCSTAnalyzer

            self._python_libcst = LibCSTAnalyzer()
        return self._python_libcst

    def analyze_project(
        self,
        root_path: str,
        analyzers: list[str] | None = None,
        package_name: str | None = None,
    ) -> CodeAnalysisResult:
        """Run all or selected analyzers on a project."""
        run_all = analyzers is None
        result = CodeAnalysisResult()

        if run_all or "tree-sitter" in analyzers:
            ts = self._get_tree_sitter().analyze_project(root_path)
            result.symbols.extend(ts.symbols)
            result.issues.extend(ts.issues)
            result.metrics.update(ts.metrics)

        if run_all or "complexity" in analyzers:
            cx = self._get_complexity().analyze_complexity(root_path)
            result.issues.extend(cx.issues)
            result.metrics.update(cx.metrics)

        if run_all or "architecture" in analyzers:
            arch = self._get_architecture().check_import_linter(root_path)
            result.issues.extend(arch.issues)
            result.metrics.update(arch.metrics)
            if package_name:
                graph = self._get_architecture().build_import_graph(root_path, package_name)
                result.dependencies.extend(graph.dependencies)
                result.metrics.update(graph.metrics)

        if run_all or "semgrep" in analyzers:
            sg = self._get_semgrep().analyze(root_path)
            result.issues.extend(sg.issues)
            result.metrics.update(sg.metrics)

        if run_all or "libcst" in analyzers:
            lc = self._get_python_libcst().analyze_directory(root_path)
            result.issues.extend(lc.issues)

        if run_all or "roslyn" in analyzers:
            root = Path(root_path)
            solution_files = list(root.glob("*.sln"))
            if solution_files:
                from beep.codeanalysis.csharp_roslyn_client import (
                    analyze_csharp_solution,
                    extract_csharp_diagnostics,
                    extract_csharp_dependencies,
                )

                sol_path = str(solution_files[0])
                sym = analyze_csharp_solution(sol_path, command="symbols")
                if sym.get("ok"):
                    result.metrics["roslyn_projects"] = len(sym.get("projects", []))
                diag = extract_csharp_diagnostics(sol_path)
                result.issues.extend(diag.issues)
                dep = extract_csharp_dependencies(sol_path)
                result.dependencies.extend(dep.dependencies)

        return result
