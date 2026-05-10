"""JavaScript language adapter."""

from __future__ import annotations

from pathlib import Path

from beep.languages._shared import deduplicate, read_package_json
from beep.languages.base import LanguageAdapter, ProjectCommand


class JavaScriptAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "javascript"

    @property
    def extensions(self) -> list[str]:
        return [".js", ".jsx", ".mjs", ".cjs"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        has_js = bool(
            list(root.rglob("*.js"))
            or list(root.rglob("*.jsx"))
            or list(root.rglob("*.mjs"))
            or list(root.rglob("*.cjs"))
        )
        if has_js and (root / "package.json").exists():
            return True
        if has_js:
            return not (root / "tsconfig.json").exists()
        return False

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        pkg = read_package_json(root)
        if not pkg:
            return []
        scripts = pkg.get("scripts", {})
        if "build" in scripts:
            return [
                ProjectCommand(
                    name="npm-build",
                    command=["npm", "run", "build"],
                    description="Build project via npm",
                )
            ]
        return []

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        pkg = read_package_json(root)
        if not pkg:
            return []
        scripts = pkg.get("scripts", {})
        deps = {**(pkg.get("devDependencies", {})), **(pkg.get("dependencies", {}))}
        if "test" in scripts:
            return [
                ProjectCommand(
                    name="npm-test",
                    command=["npm", "test"],
                    description="Run tests via npm",
                )
            ]
        if "jest" in deps:
            return [
                ProjectCommand(
                    name="jest",
                    command=["npx", "jest"],
                    description="Run Jest tests",
                )
            ]
        if "vitest" in deps:
            return [
                ProjectCommand(
                    name="vitest",
                    command=["npx", "vitest", "run"],
                    description="Run Vitest tests",
                )
            ]
        return []

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        pkg = read_package_json(root)
        if not pkg:
            return []
        deps = {**(pkg.get("devDependencies", {})), **(pkg.get("dependencies", {}))}
        scripts = pkg.get("scripts", {})
        commands: list[ProjectCommand] = []
        if "eslint" in deps:
            commands.append(
                ProjectCommand(
                    name="eslint",
                    command=["npx", "eslint", "."],
                    description="Run ESLint",
                )
            )
        if "biome" in deps:
            commands.append(
                ProjectCommand(
                    name="biome",
                    command=["npx", "@biomejs/biome", "check", "."],
                    description="Run Biome linter",
                )
            )
        if "lint" in scripts and not commands:
            commands.append(
                ProjectCommand(
                    name="npm-lint",
                    command=["npm", "run", "lint"],
                    description="Run lint script via npm",
                )
            )
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        candidates: list[str] = []
        for ext in (".test.js", ".spec.js", ".test.jsx", ".spec.jsx"):
            candidates.extend(str(p) for p in root.rglob(f"*{source_name}{ext}"))
        tests_dir = root / "__tests__"
        if tests_dir.is_dir():
            candidates.extend(str(p) for p in tests_dir.rglob(f"{source_name}.*"))
        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        pkg = read_package_json(root)
        if not pkg:
            return []
        deps = {**(pkg.get("devDependencies", {})), **(pkg.get("dependencies", {}))}
        frameworks: list[str] = []
        if "react" in deps:
            frameworks.append("React")
        if "next" in deps:
            frameworks.append("Next.js")
        if "vue" in deps:
            frameworks.append("Vue")
        if "@angular/core" in deps:
            frameworks.append("Angular")
        if "express" in deps:
            frameworks.append("Express")
        return frameworks

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "yarn.lock").exists():
            managers.append("yarn")
        if (root / "pnpm-lock.yaml").exists():
            managers.append("pnpm")
        if (root / "package-lock.json").exists() and not managers:
            managers.append("npm")
        return managers
