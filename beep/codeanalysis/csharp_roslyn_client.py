"""Python client for the C# Roslyn analyzer tool."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from beep.agent.csharp_env import check_dotnet_sdk, check_roslyn_analyzer, is_ready
from beep.codeanalysis.models import AnalysisIssue, CodeAnalysisResult

_CSHARP_ANALYZER_DIR = (
    Path(__file__).parent.parent.parent / "tools" / "Beep.CSharpAnalyzer" / "Beep.CSharpAnalyzer"
)


def _check_prerequisites() -> tuple[bool, str]:
    """Check if .NET SDK and Roslyn analyzer are ready.

    Returns:
        (is_ready, error_message)
    """
    sdk = check_dotnet_sdk()
    if not sdk.installed:
        return (
            False,
            ".NET SDK is not installed. Install from https://dotnet.microsoft.com/download",
        )
    if not sdk.meets_minimum:
        return False, f".NET SDK {sdk.version} is too old. Minimum required: 8.0"

    analyzer = check_roslyn_analyzer()
    if not analyzer["csproj_exists"]:
        return False, "Roslyn analyzer project not found. Run 'beep csharp setup'"
    if not analyzer["built"]:
        return False, "Roslyn analyzer not built. Run 'beep csharp build'"

    return True, ""


def analyze_csharp_solution(
    solution_path: str,
    command: str = "symbols",
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the Roslyn analyzer on a C# solution."""
    ready, error = _check_prerequisites()
    if not ready:
        return {"ok": False, "error": error}

    analyzer_dir = project_dir or _CSHARP_ANALYZER_DIR
    cmd = [
        "dotnet",
        "run",
        "--project",
        str(analyzer_dir),
        "--",
        "--solution",
        solution_path,
        "--command",
        command,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return {
                "ok": False,
                "error": result.stderr,
                "stdout": result.stdout,
            }
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Roslyn analyzer timed out after 120s"}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON output: {exc}"}


def analyze_csharp_project(
    project_path: str,
    command: str = "symbols",
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the Roslyn analyzer on a single .csproj file."""
    ready, error = _check_prerequisites()
    if not ready:
        return {"ok": False, "error": error}

    analyzer_dir = project_dir or _CSHARP_ANALYZER_DIR
    cmd = [
        "dotnet",
        "run",
        "--project",
        str(analyzer_dir),
        "--",
        "--project",
        project_path,
        "--command",
        command,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return {
                "ok": False,
                "error": result.stderr,
                "stdout": result.stdout,
            }
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Roslyn analyzer timed out after 120s"}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON output: {exc}"}


def extract_csharp_diagnostics(solution_path: str) -> CodeAnalysisResult:
    """Extract compiler diagnostics from a C# solution."""
    result = analyze_csharp_solution(solution_path, command="diagnostics")
    if not result.get("ok"):
        return CodeAnalysisResult(
            issues=[
                AnalysisIssue(
                    code="CS-ANALYZER",
                    message=result.get("error", "Unknown error"),
                    severity="info",
                    file_path=solution_path,
                    tool="roslyn",
                )
            ]
        )

    issues: list[AnalysisIssue] = []
    for diag in result.get("diagnostics", []):
        issues.append(
            AnalysisIssue(
                code=diag.get("code", "UNKNOWN"),
                message=diag.get("message", ""),
                severity=diag.get("severity", "warning"),
                file_path=diag.get("file", ""),
                line=diag.get("line"),
                column=diag.get("column"),
                tool="roslyn",
            )
        )

    return CodeAnalysisResult(
        issues=issues,
        metrics={"roslyn_diagnostics": len(issues)},
    )


def extract_csharp_dependencies(solution_path: str) -> CodeAnalysisResult:
    """Extract project dependencies from a C# solution."""
    result = analyze_csharp_solution(solution_path, command="dependencies")
    if not result.get("ok"):
        return CodeAnalysisResult(metrics={"roslyn_deps": "error"})

    deps = result.get("dependencies", [])
    return CodeAnalysisResult(
        dependencies=deps,
        metrics={"roslyn_project_count": len(deps)},
    )
