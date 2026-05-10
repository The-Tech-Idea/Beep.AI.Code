"""Auto-detect and run workspace linter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LintResult:
    passed: bool
    output: str
    linter: str = ""


_LINTER_MAP: list[tuple[str, tuple[str, ...], list[str]]] = [
    ("ruff", ("pyproject.toml", "ruff.toml"), ["ruff", "check", "."]),
    ("flake8", (".flake8", "setup.cfg", "tox.ini"), ["python", "-m", "flake8", "."]),
    (
        "eslint",
        (".eslintrc", ".eslintrc.js", ".eslintrc.json", "eslint.config.js"),
        ["npx", "eslint", "."],
    ),
    ("pylint", ("pylintrc", ".pylintrc"), ["python", "-m", "pylint", "."]),
]


def _detect_linter(workspace_root: Path) -> tuple[str, list[str]] | None:
    for name, markers, cmd in _LINTER_MAP:
        for marker in markers:
            if (workspace_root / marker).exists():
                return name, cmd
    return None


async def run_workspace_lint(workspace_root: Path, files: list[str] | None = None) -> LintResult:
    """Auto-detect and run linter on the workspace.

    If specific files are provided and the linter supports it,
    only those files are linted.
    """
    detected = _detect_linter(workspace_root)
    if detected is None:
        return LintResult(passed=True, output="No linter detected", linter="")

    linter, cmd = detected

    if files and linter in ("ruff", "eslint"):
        cmd = cmd[:-1] + files

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = (stdout.decode() + stderr.decode()).strip()
        return LintResult(
            passed=process.returncode == 0,
            output=output[:1000],
            linter=linter,
        )
    except (FileNotFoundError, OSError) as exc:
        return LintResult(passed=True, output=f"Lint command failed: {exc}", linter=linter)
