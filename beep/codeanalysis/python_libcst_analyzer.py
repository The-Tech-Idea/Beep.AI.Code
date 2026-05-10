"""Python-specific code analyzer using LibCST."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from beep.codeanalysis.models import AnalysisIssue, CodeAnalysisResult


class LibCSTAnalyzer:
    """Analyze Python code using LibCST for safe AST-based analysis."""

    def analyze_file(self, file_path: str) -> CodeAnalysisResult:
        """Analyze a single Python file for issues."""
        source = Path(file_path).read_text(encoding="utf-8")
        try:
            tree = cst.parse_module(source)
        except cst.ParserSyntaxError as exc:
            return CodeAnalysisResult(
                issues=[
                    AnalysisIssue(
                        code="LIBCST-001",
                        message=f"Syntax error: {exc}",
                        severity="error",
                        file_path=file_path,
                        tool="libcst",
                    )
                ]
            )

        issues: list[AnalysisIssue] = []
        collector = _PythonIssueCollector()
        tree.visit(collector)
        for node_type, node in collector.issues:
            issues.append(
                AnalysisIssue(
                    code=f"LIBCST-{node_type}",
                    message=self._describe_issue(node_type, node),
                    severity="warning",
                    file_path=file_path,
                    line=node.start_line if hasattr(node, "start_line") else None,
                    tool="libcst",
                )
            )
        return CodeAnalysisResult(issues=issues)

    def analyze_directory(self, dir_path: str) -> CodeAnalysisResult:
        """Analyze all Python files in a directory."""
        all_issues: list[AnalysisIssue] = []
        for py_file in Path(dir_path).rglob("*.py"):
            if any(
                skip in py_file.parts for skip in (".venv", "venv", "node_modules", "__pycache__")
            ):
                continue
            result = self.analyze_file(str(py_file))
            all_issues.extend(result.issues)
        return CodeAnalysisResult(issues=all_issues)

    @staticmethod
    def _describe_issue(node_type: str, node: cst.CSTNode) -> str:
        descriptions = {
            "bare_except": "Bare except clause — specify the exception type",
            "pass_in_function": "Empty function body with only pass",
        }
        return descriptions.get(node_type, f"LibCST detected issue: {node_type}")


class _PythonIssueCollector(cst.CSTVisitor):
    def __init__(self) -> None:
        self.issues: list[tuple[str, cst.CSTNode]] = []

    def visit_Try(self, node: cst.Try) -> None:
        for handler in node.handlers:
            if handler.type is None:
                self.issues.append(("bare_except", node))

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if len(node.body.body) == 1 and isinstance(node.body.body[0], (cst.Pass,)):
            self.issues.append(("pass_in_function", node))
