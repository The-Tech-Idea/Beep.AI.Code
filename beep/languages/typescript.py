"""TypeScript language adapter."""

from __future__ import annotations

from pathlib import Path

from beep.languages._shared import deduplicate, read_package_json
from beep.languages.base import LanguageAdapter, ProjectCommand


class TypeScriptAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "typescript"

    @property
    def extensions(self) -> list[str]:
        return [".ts", ".tsx", ".mts", ".cts"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        has_ts = bool(list(root.rglob("*.ts")) or list(root.rglob("*.tsx")))
        return has_ts and (root / "tsconfig.json").exists()

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        if (root / "tsconfig.json").exists():
            commands.append(
                ProjectCommand(
                    name="tsc",
                    command=["npx", "tsc", "--noEmit"],
                    description="Type-check TypeScript project",
                )
            )
        pkg = read_package_json(root)
        if pkg and "build" in pkg.get("scripts", {}):
            commands.append(
                ProjectCommand(
                    name="npm-build",
                    command=["npm", "run", "build"],
                    description="Build project via npm",
                )
            )
        return commands

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
        if (
            "jest" in deps
            or (root / "jest.config.js").exists()
            or (root / "jest.config.ts").exists()
        ):
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
        commands: list[ProjectCommand] = []
        if "eslint" in deps:
            commands.append(
                ProjectCommand(
                    name="eslint",
                    command=["npx", "eslint", "."],
                    description="Run ESLint for TypeScript",
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
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        candidates: list[str] = []
        for ext in (".test.ts", ".spec.ts", ".test.tsx", ".spec.tsx"):
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
        if "@angular/core" in deps:
            frameworks.append("Angular")
        if "svelte" in deps:
            frameworks.append("Svelte")
        if "@nestjs/core" in deps:
            frameworks.append("NestJS")
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
