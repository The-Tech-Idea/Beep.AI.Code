"""Lint and auto-fix integration.

Provides:
- Detect linters (ruff, eslint, flake8, etc.)
- Run linting
- Auto-fix issues
- Format code
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.panel import Panel



from beep.utils.console import get_console
class LinterType(Enum):
    """Detected linter."""

    RUFF = "ruff"
    FLAKE8 = "flake8"
    PYLINT = "pylint"
    ESLINT = "eslint"
    BIOME = "biome"
    BLACK = "black"
    PRETTIER = "prettier"
    UNKNOWN = "unknown"


@dataclass
class LintResult:
    """Result of a lint run."""

    issues: int = 0
    fixable: int = 0
    output: str = ""
    linter: LinterType = LinterType.UNKNOWN
    fixed: int = 0

    @property
    def is_clean(self) -> bool:
        return self.issues == 0


def detect_linters(workspace_root: Path) -> list[LinterType]:
    """Detect available linters in the project."""
    linters = []

    config_files = {
        LinterType.RUFF: ["ruff.toml", ".ruff.toml", "pyproject.toml"],
        LinterType.FLAKE8: [".flake8", "setup.cfg"],
        LinterType.PYLINT: [".pylintrc", "pylintrc"],
        LinterType.ESLINT: [".eslintrc", ".eslintrc.js", ".eslintrc.json", "eslint.config.js"],
        LinterType.BIOME: ["biome.json", "biome.jsonc"],
        LinterType.BLACK: ["pyproject.toml"],
        LinterType.PRETTIER: [".prettierrc", ".prettierrc.json", "prettier.config.js"],
    }

    for linter, files in config_files.items():
        for f in files:
            if (workspace_root / f).exists():
                linters.append(linter)
                break

    if not linters:
        if (workspace_root / "pyproject.toml").exists():
            linters.append(LinterType.RUFF)

    return linters


def get_lint_command(
    linter: LinterType,
    file_path: str | None = None,
    fix: bool = False,
) -> list[str]:
    """Get the lint command."""
    target = [file_path] if file_path else ["."]

    if linter == LinterType.RUFF:
        cmd = ["ruff", "check"]
        if fix:
            cmd.append("--fix")
        return cmd + target

    if linter == LinterType.FLAKE8:
        return ["flake8"] + target

    if linter == LinterType.PYLINT:
        return ["pylint"] + target

    if linter == LinterType.ESLINT:
        cmd = ["npx", "eslint"]
        if fix:
            cmd.append("--fix")
        return cmd + target

    if linter == LinterType.BIOME:
        cmd = ["npx", "@biomejs/biome", "check"]
        if fix:
            cmd.append("--apply")
        return cmd + target

    if linter == LinterType.BLACK:
        return ["black"] + target

    if linter == LinterType.PRETTIER:
        cmd = ["npx", "prettier", "--write"] if fix else ["npx", "prettier", "--check"]
        return cmd + target

    return ["ruff", "check"] + target


async def run_lint(
    workspace_root: Path,
    linter: LinterType | None = None,
    file_path: str | None = None,
    fix: bool = False,
) -> LintResult:
    """Run linting and optionally fix issues."""
    linters = [linter] if linter else detect_linters(workspace_root)
    if not linters:
        linters = [LinterType.RUFF]

    result = LintResult()
    all_output = []

    for linter in linters:
        cmd = get_lint_command(linter, file_path, fix)
        result.linter = linter

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_root,
            )

            stdout, stderr = await process.communicate()
            output = (stdout.decode("utf-8", errors="replace")
                      + stderr.decode("utf-8", errors="replace"))
            all_output.append(output)

            if linter == LinterType.RUFF:
                for line in output.splitlines():
                    if "E" in line or "F" in line or "W" in line:
                        result.issues += 1
                        if "fixable" in line.lower() or "--fix" in line.lower():
                            result.fixable += 1

            if fix and process.returncode == 0:
                result.fixed = result.issues

        except FileNotFoundError:
            all_output.append(f"Linter not found: {linter.value}")

    result.output = "\n".join(all_output)
    return result


def display_lint_result(result: LintResult) -> None:
    """Display lint results."""
    status = "[green]CLEAN[/green]" if result.is_clean else "[yellow]ISSUES FOUND[/yellow]"

    content = (
        f"[bold]Linter:[/bold] {result.linter.value}\n"
        f"[bold]Status:[/bold] {status}\n"
        f"[bold]Issues:[/bold] {result.issues}"
    )

    if result.fixable > 0:
        content += f"\n[bold]Fixable:[/bold] {result.fixable}"

    if result.fixed > 0:
        content += f"\n[bold]Fixed:[/bold] {result.fixed}"

    get_console().print(Panel(
        content,
        title="Lint Results",
        border_style="green" if result.is_clean else "yellow",
    ))

    if result.output and not result.is_clean:
        get_console().print("\n[dim]" + result.output[:1000] + "[/dim]")
