"""Tree-sitter based code analyzer for multi-language symbol extraction."""

from __future__ import annotations

from pathlib import Path

from beep.codeanalysis.models import AnalysisIssue, CodeAnalysisResult
from beep.codeindex.symbols import CodeSymbol


class TreeSitterAnalyzer:
    """Multi-language code analyzer using tree-sitter."""

    def __init__(self) -> None:
        from beep.app_service import get_app_service

        self._parser = get_app_service().tree_sitter_parser

    def analyze_file(self, file_path: str) -> list[CodeSymbol]:
        """Extract symbols from a single file."""
        return self._parser.parse_file(file_path)

    def analyze_directory(
        self, dir_path: str, extensions: list[str] | None = None
    ) -> list[CodeSymbol]:
        """Extract symbols from all files in a directory."""
        return self._parser.parse_directory(dir_path, extensions)

    def analyze_project(self, root_path: str) -> CodeAnalysisResult:
        """Full project analysis: symbols + structural issues."""
        symbols = self._parser.parse_directory(root_path)
        issues: list[AnalysisIssue] = []
        for sym in symbols:
            if sym.kind in ("function", "method"):
                line_count = sym.end_line - sym.start_line
                if line_count > 100:
                    issues.append(
                        AnalysisIssue(
                            code="TREE-SITTER-001",
                            message=f"Function '{sym.name}' is {line_count} lines long",
                            severity="warning",
                            file_path=sym.file_path,
                            line=sym.start_line,
                            tool="tree-sitter",
                        )
                    )
        return CodeAnalysisResult(
            symbols=symbols,
            issues=issues,
            metrics={"total_symbols": len(symbols)},
        )
