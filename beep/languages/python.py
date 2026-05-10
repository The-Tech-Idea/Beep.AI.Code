"""Python language adapter."""

from __future__ import annotations

from pathlib import Path

from beep.languages._shared import deduplicate
from beep.languages.base import LanguageAdapter, ProjectCommand


class PythonAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "python"

    @property
    def extensions(self) -> list[str]:
        return [".py"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        indicators = [
            root / "pyproject.toml",
            root / "requirements.txt",
            root / "setup.py",
            root / "setup.cfg",
            root / "pytest.ini",
            root / "tox.ini",
        ]
        return any(p.exists() for p in indicators) or bool(list(root.rglob("*.py")))

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        return []

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        if (
            (root / "pytest.ini").exists()
            or (root / "tests").is_dir()
            or (root / "test").is_dir()
            or _has_pyproject_tool(root, "pytest")
        ):
            return [
                ProjectCommand(
                    name="pytest",
                    command=["pytest"],
                    description="Run Python tests with pytest",
                )
            ]
        return [
            ProjectCommand(
                name="python-unittest",
                command=["python", "-m", "unittest", "discover"],
                description="Run Python unittest discovery",
            )
        ]

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        if (root / "ruff.toml").exists() or _has_pyproject_tool(root, "ruff"):
            commands.append(
                ProjectCommand(
                    name="ruff",
                    command=["ruff", "check", "."],
                    description="Run Ruff linter",
                )
            )
        if (root / ".flake8").exists() or (root / "setup.cfg").exists():
            commands.append(
                ProjectCommand(
                    name="flake8",
                    command=["flake8", "."],
                    description="Run Flake8 linter",
                )
            )
        if _has_pyproject_dep(root, "pylint") or (root / ".pylintrc").exists():
            commands.append(
                ProjectCommand(
                    name="pylint",
                    command=["pylint", "."],
                    description="Run Pylint linter",
                )
            )
        if _has_pyproject_dep(root, "mypy") or (root / "mypy.ini").exists():
            commands.append(
                ProjectCommand(
                    name="mypy",
                    command=["mypy", "."],
                    description="Run mypy type checker",
                )
            )
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        source = Path(source_file)
        root = Path(root_path)
        stem = source.stem
        candidates = [
            root / "tests" / f"test_{source.name}",
            root / "tests" / f"{stem}_test.py",
            source.with_name(f"test_{source.name}"),
            source.with_name(f"{stem}_test.py"),
            root / "test" / f"test_{source.name}",
        ]
        return deduplicate([str(p) for p in candidates if p.exists()])

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        if (root / "manage.py").exists():
            frameworks.append("Django")
        if _has_pyproject_dep(root, "fastapi") or _has_requirement(root, "fastapi"):
            frameworks.append("FastAPI")
        if _has_pyproject_dep(root, "flask") or _has_requirement(root, "flask"):
            frameworks.append("Flask")
        return frameworks

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "pyproject.toml").exists():
            if _has_pyproject_tool(root, "poetry"):
                managers.append("poetry")
            elif _has_pyproject_tool(root, "hatch"):
                managers.append("hatch")
            else:
                managers.append("pip")
        if (root / "Pipfile").exists():
            managers.append("pipenv")
        if (root / "requirements.txt").exists() and not managers:
            managers.append("pip")
        return managers


def _has_pyproject_tool(root: Path, tool: str) -> bool:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return False
    content = pyproject.read_text(encoding="utf-8")
    return f"[tool.{tool}]" in content or f'"{tool}"' in content


def _has_pyproject_dep(root: Path, dep: str) -> bool:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return False
    return dep.lower() in pyproject.read_text(encoding="utf-8").lower()


def _has_requirement(root: Path, dep: str) -> bool:
    req = root / "requirements.txt"
    if not req.exists():
        return False
    return dep.lower() in req.read_text(encoding="utf-8").lower()
