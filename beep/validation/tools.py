"""Validation tools using ruff, import-linter, and other static checkers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from beep.validation.policy import ValidationResult


def run_ruff_check(workspace_root: Path, fix: bool = False) -> ValidationResult:
    cmd = ["ruff", "check", "."]
    if fix:
        cmd.append("--fix")
    return _run_command("ruff", cmd, workspace_root)


def run_ruff_format(workspace_root: Path, check_only: bool = False) -> ValidationResult:
    cmd = ["ruff", "format", "."]
    if check_only:
        cmd.append("--check")
    return _run_command("ruff-format", cmd, workspace_root)


def run_import_linter(workspace_root: Path) -> ValidationResult:
    config = workspace_root / ".importlinter"
    if not config.exists():
        return ValidationResult(
            step="import-linter",
            success=True,
            output="No .importlinter config found — skipping.",
        )
    return _run_command("import-linter", ["lint-imports"], workspace_root)


def run_mypy(workspace_root: Path) -> ValidationResult:
    return _run_command("mypy", ["mypy", "."], workspace_root)


def run_bandit(workspace_root: Path) -> ValidationResult:
    return _run_command("bandit", ["bandit", "-r", "."], workspace_root)


def run_radon_complexity(workspace_root: Path) -> ValidationResult:
    return _run_command("radon", ["radon", "cc", ".", "--nc"], workspace_root)


def run_vulture(workspace_root: Path) -> ValidationResult:
    return _run_command("vulture", ["vulture", "."], workspace_root)


def _run_command(name: str, cmd: list[str], cwd: Path) -> ValidationResult:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        success = result.returncode == 0
        if not output and error:
            output = error
        return ValidationResult(
            step=name,
            success=success,
            output=output[:2000],
            error=error[:500] if not success else "",
            command=" ".join(cmd),
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            step=name,
            success=False,
            error=f"{name} timed out after 60s",
            command=" ".join(cmd),
        )
    except FileNotFoundError:
        return ValidationResult(
            step=name,
            success=True,
            output=f"{name} is not installed — skipping.",
            command=" ".join(cmd),
        )
    except Exception as exc:
        return ValidationResult(
            step=name,
            success=False,
            error=str(exc),
            command=" ".join(cmd),
        )
