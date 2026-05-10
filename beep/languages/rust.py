"""Rust language adapter."""

from __future__ import annotations

from pathlib import Path

from beep.languages._shared import deduplicate
from beep.languages.base import LanguageAdapter, ProjectCommand


class RustAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "rust"

    @property
    def extensions(self) -> list[str]:
        return [".rs"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        return (root / "Cargo.toml").exists() or bool(list(root.rglob("*.rs")))

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        return [
            ProjectCommand(
                name="cargo-build",
                command=["cargo", "build"],
                description="Build Rust project with Cargo",
            )
        ]

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        return [
            ProjectCommand(
                name="cargo-test",
                command=["cargo", "test"],
                description="Run Rust tests with Cargo",
            )
        ]

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        commands: list[ProjectCommand] = []
        commands.append(
            ProjectCommand(
                name="cargo-clippy",
                command=["cargo", "clippy", "--", "-D", "warnings"],
                description="Run Clippy linter",
            )
        )
        commands.append(
            ProjectCommand(
                name="cargo-fmt",
                command=["cargo", "fmt", "--", "--check"],
                description="Check Rust code formatting",
            )
        )
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source = Path(source_file)
        source_name = source.stem
        candidates: list[str] = []

        if "tests" in source.parts:
            candidates.append(str(source))

        tests_dir = root / "tests"
        if tests_dir.is_dir():
            candidates.extend(str(p) for p in tests_dir.rglob(f"*{source_name}*.rs"))

        src_integration = root / "src"
        if src_integration.is_dir():
            candidates.extend(str(p) for p in src_integration.rglob(f"*{source_name}*test*.rs"))

        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        cargo_toml = root / "Cargo.toml"
        if cargo_toml.exists():
            content = cargo_toml.read_text(encoding="utf-8").lower()
            if "actix-web" in content:
                frameworks.append("Actix Web")
            if "tokio" in content:
                frameworks.append("Tokio")
            if "axum" in content:
                frameworks.append("Axum")
            if "rocket" in content:
                frameworks.append("Rocket")
            if "serde" in content:
                frameworks.append("Serde")
            if "diesel" in content:
                frameworks.append("Diesel")
            if "sqlx" in content:
                frameworks.append("SQLx")
        return deduplicate(frameworks)

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "Cargo.toml").exists():
            managers.append("cargo")
        return managers
