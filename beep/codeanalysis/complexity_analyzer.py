"""Complexity analyzer using radon."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from beep.codeanalysis.models import AnalysisIssue, CodeAnalysisResult


class ComplexityAnalyzer:
    """Analyze code complexity using radon."""

    def analyze_complexity(self, root_path: str, threshold: int = 10) -> CodeAnalysisResult:
        """Run radon cyclomatic complexity analysis."""
        issues: list[AnalysisIssue] = []
        metrics: dict[str, object] = {}

        try:
            result = subprocess.run(
                ["radon", "cc", root_path, "--json", "--min", str(threshold)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 or result.stdout:
                data = json.loads(result.stdout) if result.stdout.strip() else {}
                for file_path, blocks in data.items():
                    for block in blocks:
                        severity = "error" if block.get("rank", "A") in ("E", "F") else "warning"
                        issues.append(
                            AnalysisIssue(
                                code=f"COMPLEXITY-{block.get('rank', '?')}",
                                message=f"Complexity {block.get('complexity')} for {block.get('type')} '{block.get('name')}'",
                                severity=severity,
                                file_path=file_path,
                                line=block.get("line"),
                                tool="radon",
                            )
                        )
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

        try:
            mi_result = subprocess.run(
                ["radon", "mi", root_path, "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if mi_result.stdout.strip():
                mi_data = json.loads(mi_result.stdout)
                avg_mi = 0
                low_mi_files = []
                for file_path, score in mi_data.items():
                    mi = score.get("mi", 0)
                    if mi < 20:
                        low_mi_files.append(file_path)
                    avg_mi += mi
                if mi_data:
                    avg_mi /= len(mi_data)
                metrics["avg_maintainability_index"] = round(avg_mi, 2)
                metrics["low_mi_file_count"] = len(low_mi_files)
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

        return CodeAnalysisResult(
            issues=issues,
            metrics=metrics,
        )
