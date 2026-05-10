"""Go language adapter."""

from __future__ import annotations

from pathlib import Path

from beep.languages._shared import deduplicate, has_tool
from beep.languages.base import LanguageAdapter, ProjectCommand


class GoAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "go"

    @property
    def extensions(self) -> list[str]:
        return [".go"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        return (root / "go.mod").exists() or bool(list(root.rglob("*.go")))

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        if (root / "go.mod").exists():
            return [
                ProjectCommand(
                    name="go-build",
                    command=["go", "build", "./..."],
                    description="Build Go project",
                )
            ]
        return [
            ProjectCommand(
                name="go-build",
                command=["go", "build"],
                description="Build Go project",
            )
        ]

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        return [
            ProjectCommand(
                name="go-test",
                command=["go", "test", "./..."],
                description="Run Go tests",
            )
        ]

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        has_golangci = (root / ".golangci.yml").exists() or (root / ".golangci.yaml").exists()
        if has_tool("golangci-lint") or has_golangci:
            commands.append(
                ProjectCommand(
                    name="golangci-lint",
                    command=["golangci-lint", "run"],
                    description="Run golangci-lint",
                )
            )
        if has_tool("staticcheck"):
            commands.append(
                ProjectCommand(
                    name="staticcheck",
                    command=["staticcheck", "./..."],
                    description="Run staticcheck",
                )
            )
        if not commands:
            commands.append(
                ProjectCommand(
                    name="go-vet",
                    command=["go", "vet", "./..."],
                    description="Run go vet",
                )
            )
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        test_name = f"{source_name}_test.go"
        candidates: list[str] = []
        for p in root.rglob(test_name):
            candidates.append(str(p))
        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        for go_file in root.rglob("*.go"):
            try:
                content = go_file.read_text(encoding="utf-8").lower()
            except (OSError, UnicodeDecodeError):
                continue
            if "github.com/gin-gonic/gin" in content:
                frameworks.append("Gin")
            if "github.com/gorilla/mux" in content:
                frameworks.append("Gorilla Mux")
            if "github.com/labstack/echo" in content:
                frameworks.append("Echo")
            if "github.com/go-chi/chi" in content:
                frameworks.append("Chi")
            if "google.golang.org/grpc" in content:
                frameworks.append("gRPC")
            if "github.com/stretchr/testify" in content:
                if "Testify" not in frameworks:
                    frameworks.append("Testify")
        return deduplicate(frameworks)

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "go.mod").exists():
            managers.append("go-modules")
        return managers
