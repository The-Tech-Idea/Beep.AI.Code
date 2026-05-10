"""Semgrep analyzer for security and custom rules."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from beep.codeanalysis.models import AnalysisIssue, CodeAnalysisResult


class SemgrepAnalyzer:
    """Run semgrep for security and custom rule analysis."""

    def analyze(self, root_path: str, config: str = "auto") -> CodeAnalysisResult:
        """Run semgrep with the specified config."""
        issues: list[AnalysisIssue] = []
        try:
            result = subprocess.run(
                ["semgrep", "--json", "--config", config, "--quiet", root_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                for finding in data.get("results", []):
                    extra = finding.get("extra", {})
                    severity = self._map_severity(extra.get("severity", "INFO"))
                    issues.append(
                        AnalysisIssue(
                            code=extra.get("id", "SEMGREP"),
                            message=extra.get("message", ""),
                            severity=severity,
                            file_path=finding.get("path", ""),
                            line=finding.get("start", {}).get("line"),
                            column=finding.get("start", {}).get("col"),
                            tool="semgrep",
                        )
                    )
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
        return CodeAnalysisResult(
            issues=issues,
            metrics={"semgrep_issues": len(issues)},
        )

    @staticmethod
    def _map_severity(raw: str) -> str:
        mapping = {"INFO": "info", "WARNING": "warning", "ERROR": "error"}
        return mapping.get(raw.upper(), "info")
