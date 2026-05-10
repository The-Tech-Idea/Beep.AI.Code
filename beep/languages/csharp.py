"""C# / .NET language adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.codeanalysis.models import CodeAnalysisResult
from beep.languages._shared import deduplicate
from beep.languages.base import LanguageAdapter, ProjectCommand


class CSharpAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "csharp"

    @property
    def extensions(self) -> list[str]:
        return [".cs", ".csproj", ".sln", ".razor"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        return bool(list(root.glob("*.sln")) or list(root.rglob("*.csproj")))

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        solution_files = list(root.glob("*.sln"))
        if solution_files:
            return [
                ProjectCommand(
                    name="dotnet-build",
                    command=["dotnet", "build", str(solution_files[0])],
                    description="Build .NET solution",
                )
            ]
        return [
            ProjectCommand(
                name="dotnet-build",
                command=["dotnet", "build"],
                description="Build .NET project",
            )
        ]

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        return [
            ProjectCommand(
                name="dotnet-test",
                command=["dotnet", "test"],
                description="Run .NET tests",
            )
        ]

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        return [
            ProjectCommand(
                name="dotnet-format",
                command=["dotnet", "format", "--verify-no-changes"],
                description="Check .NET code formatting",
            )
        ]

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        candidates: list[str] = []
        for file in root.rglob("*.cs"):
            if source_name in file.stem and ("Test" in file.stem or "Tests" in str(file)):
                candidates.append(str(file))
        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        for csproj in root.rglob("*.csproj"):
            content = csproj.read_text(encoding="utf-8").lower()
            if "microsoft.net.sdk.web" in content:
                if "microsoft.aspnetcore.components" in content:
                    frameworks.append("Blazor")
                else:
                    frameworks.append("ASP.NET Core")
            if "microsoft.net.sdk.windowsdesktop" in content:
                if "usewpf" in content:
                    frameworks.append("WPF")
                if "usewindowsforms" in content:
                    frameworks.append("WinForms")
            if "maui" in content:
                frameworks.append("MAUI")
        if not frameworks:
            proj_files = list(root.rglob("*.csproj"))
            if proj_files:
                frameworks.append(".NET (detected via .csproj)")
        return deduplicate(frameworks)

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if any(f.name.lower() == "nuget.config" for f in root.iterdir() if f.is_file()):
            managers.append("NuGet")
        if list(root.rglob("*.csproj")) and not managers:
            managers.append("dotnet")
        return managers

    def analyze_symbols(self, root_path: str) -> dict[str, Any]:
        """Use Roslyn to extract symbols from the solution."""
        from beep.codeanalysis.csharp_roslyn_client import analyze_csharp_solution

        root = Path(root_path)
        solution_files = list(root.glob("*.sln"))
        if not solution_files:
            return {"ok": False, "error": "No .sln file found."}
        return analyze_csharp_solution(str(solution_files[0]), command="symbols")

    def analyze_diagnostics(self, root_path: str) -> CodeAnalysisResult:
        """Use Roslyn to extract compiler diagnostics."""
        from beep.codeanalysis.csharp_roslyn_client import extract_csharp_diagnostics

        root = Path(root_path)
        solution_files = list(root.glob("*.sln"))
        if not solution_files:
            return CodeAnalysisResult()
        return extract_csharp_diagnostics(str(solution_files[0]))

    def analyze_dependencies(self, root_path: str) -> CodeAnalysisResult:
        """Use Roslyn to extract project dependencies."""
        from beep.codeanalysis.csharp_roslyn_client import extract_csharp_dependencies

        root = Path(root_path)
        solution_files = list(root.glob("*.sln"))
        if not solution_files:
            return CodeAnalysisResult()
        return extract_csharp_dependencies(str(solution_files[0]))
