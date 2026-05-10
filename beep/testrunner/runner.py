"""Test runner integration.

Provides:
- Detect test framework (pytest, jest, unittest, etc.)
- Run tests for changed files
- Run all tests
- Watch mode
- Test result parsing
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.panel import Panel



from beep.utils.console import get_console
class TestFramework(Enum):
    """Detected test framework."""

    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    VITEST = "vitest"
    MOCHA = "mocha"
    GO_TEST = "go test"
    CARGO_TEST = "cargo test"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    """Result of a test run."""

    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    output: str = ""
    framework: TestFramework = TestFramework.UNKNOWN

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.errors == 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors


def detect_framework(workspace_root: Path) -> TestFramework:
    """Detect the test framework used in the project."""
    indicators = {
        TestFramework.PYTEST: [
            "pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py",
        ],
        TestFramework.JEST: [
            "jest.config.js", "jest.config.ts", "jest.config.json",
        ],
        TestFramework.VITEST: [
            "vitest.config.ts", "vitest.config.js",
        ],
        TestFramework.MOCHA: [
            ".mocharc.js", ".mocharc.json",
        ],
        TestFramework.GO_TEST: [
            "go.mod",
        ],
        TestFramework.CARGO_TEST: [
            "Cargo.toml",
        ],
    }

    for framework, files in indicators.items():
        for f in files:
            if (workspace_root / f).exists():
                return framework

    if (workspace_root / "package.json").exists():
        pkg = (workspace_root / "package.json").read_text()
        if "jest" in pkg.lower():
            return TestFramework.JEST
        if "vitest" in pkg.lower():
            return TestFramework.VITEST

    return TestFramework.UNKNOWN


def get_test_command(
    framework: TestFramework,
    file_path: str | None = None,
    watch: bool = False,
) -> list[str]:
    """Get the test command for a framework."""
    if framework == TestFramework.PYTEST:
        cmd = ["pytest", "-v", "--tb=short"]
        if file_path:
            cmd.append(file_path)
        if watch:
            cmd.extend(["--watch"])
        return cmd

    if framework == TestFramework.JEST:
        cmd = ["npx", "jest"]
        if file_path:
            cmd.append(file_path)
        if watch:
            cmd.append("--watch")
        return cmd

    if framework == TestFramework.VITEST:
        cmd = ["npx", "vitest", "run"]
        if file_path:
            cmd.extend(["--reporter", "verbose", file_path])
        if watch:
            cmd = ["npx", "vitest"]
        return cmd

    if framework == TestFramework.GO_TEST:
        cmd = ["go", "test", "-v"]
        if file_path:
            cmd.append(str(Path(file_path).parent))
        return cmd

    if framework == TestFramework.CARGO_TEST:
        return ["cargo", "test"]

    return ["pytest", "-v"]


async def run_tests(
    workspace_root: Path,
    framework: TestFramework | None = None,
    file_path: str | None = None,
    watch: bool = False,
    timeout: int = 120,
) -> TestResult:
    """Run tests and parse results."""
    fw = framework or detect_framework(workspace_root)
    if fw == TestFramework.UNKNOWN:
        fw = TestFramework.PYTEST

    cmd = get_test_command(fw, file_path, watch)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_root,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "FORCE_COLOR": "1"},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except TimeoutError:
            process.kill()
            return TestResult(
                framework=fw,
                output="Tests timed out",
                errors=1,
            )

        output = (stdout.decode("utf-8", errors="replace")
                  + stderr.decode("utf-8", errors="replace"))

        result = _parse_test_output(output, fw)
        result.framework = fw
        return result

    except FileNotFoundError:
        return TestResult(
            framework=fw,
            output=f"Command not found: {cmd[0]}",
            errors=1,
        )


def _parse_test_output(output: str, framework: TestFramework) -> TestResult:
    """Parse test output into structured results."""
    result = TestResult(output=output)

    if framework == TestFramework.PYTEST:
        for line in output.splitlines():
            if "passed" in line:
                import re
                passed = re.search(r"(\d+) passed", line)
                failed = re.search(r"(\d+) failed", line)
                skipped = re.search(r"(\d+) skipped", line)
                errors = re.search(r"(\d+) error", line)
                duration = re.search(r"in ([\d.]+)s", line)

                if passed:
                    result.passed = int(passed.group(1))
                if failed:
                    result.failed = int(failed.group(1))
                if skipped:
                    result.skipped = int(skipped.group(1))
                if errors:
                    result.errors = int(errors.group(1))
                if duration:
                    result.duration = float(duration.group(1))
                break

    return result


def display_test_result(result: TestResult) -> None:
    """Display test results with Rich formatting."""
    status = "[green]PASSED[/green]" if result.success else "[red]FAILED[/red]"

    get_console().print(Panel(
        f"[bold]Framework:[/bold] {result.framework.value}\n"
        f"[bold]Status:[/bold] {status}\n\n"
        f"[green]Passed:[/green] {result.passed}\n"
        f"[red]Failed:[/red] {result.failed}\n"
        f"[yellow]Skipped:[/yellow] {result.skipped}\n"
        f"[red]Errors:[/red] {result.errors}\n"
        f"[dim]Duration:[/dim] {result.duration:.2f}s",
        title="Test Results",
        border_style="green" if result.success else "red",
    ))

    if not result.success:
        get_console().print("\n[yellow]Test Output:[/yellow]")
        get_console().print(result.output[-2000:])
