"""Architecture and import graph analyzer."""

from __future__ import annotations

import subprocess
from pathlib import Path

from beep.codeanalysis.models import AnalysisIssue, CodeAnalysisResult


class ArchitectureAnalyzer:
    """Analyze architecture boundaries using import-linter and grimp."""

    def check_import_linter(self, root_path: str) -> CodeAnalysisResult:
        """Run import-linter to check architecture boundaries."""
        config = Path(root_path) / ".importlinter"
        if not config.exists():
            return CodeAnalysisResult(
                issues=[],
                metrics={"import_linter": "no config found"},
            )
        issues: list[AnalysisIssue] = []
        try:
            result = subprocess.run(
                ["lint-imports"],
                cwd=root_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                for line in result.stdout.splitlines():
                    if "Forbidden" in line or "import" in line.lower():
                        issues.append(
                            AnalysisIssue(
                                code="ARCH-001",
                                message=line.strip(),
                                severity="error",
                                file_path=str(config),
                                tool="import-linter",
                            )
                        )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return CodeAnalysisResult(
            issues=issues,
            metrics={"import_linter": "passed" if not issues else "violations found"},
        )

    def build_import_graph(self, root_path: str, package_name: str) -> CodeAnalysisResult:
        """Build import dependency graph using grimp."""
        try:
            import grimp

            graph = grimp.build_graph(package_name, root_path=root_path)
            dependencies = []
            for module in graph.modules:
                for imported in graph.find_modules_that_import(module):
                    dependencies.append({"from": imported, "to": module})
            return CodeAnalysisResult(
                dependencies=dependencies,
                metrics={
                    "module_count": len(graph.modules),
                    "dependency_count": len(dependencies),
                },
            )
        except ImportError:
            return CodeAnalysisResult(metrics={"grimp": "not installed"})
        except Exception as exc:
            return CodeAnalysisResult(
                issues=[
                    AnalysisIssue(
                        code="GRAPH-001",
                        message=f"Failed to build import graph: {exc}",
                        severity="info",
                        file_path=root_path,
                        tool="grimp",
                    )
                ]
            )
