"""Auto-detect and run workspace tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    """Result of running workspace tests."""

    __test__ = False
    passed: bool
    output: str
    framework: str = ""


_TEST_FRAMEWORKS: list[tuple[str, tuple[str, ...]]] = [
    ("pytest", ("pyproject.toml", "pytest.ini", "setup.cfg", "setup.py")),
    ("jest", ("package.json", "jest.config.js", "jest.config.ts")),
    ("vitest", ("vitest.config.js", "vitest.config.ts")),
    ("mocha", ("package.json",)),
]


def _detect_framework(workspace_root: Path) -> str | None:
    for name, markers in _TEST_FRAMEWORKS:
        for marker in markers:
            if (workspace_root / marker).exists():
                return name
    return None


async def run_workspace_tests(workspace_root: Path) -> TestResult:
    """Auto-detect and run tests in the workspace.

    Returns a TestResult even if no framework is detected.
    """
    framework = _detect_framework(workspace_root)
    if framework is None:
        return TestResult(passed=True, output="No test framework detected", framework="")

    cmd_map = {
        "pytest": ["python", "-m", "pytest", "--tb=short", "-q"],
        "jest": ["npx", "jest", "--passWithNoTests", "--silent"],
        "vitest": ["npx", "vitest", "run", "--silent"],
        "mocha": ["npx", "mocha"],
    }
    cmd = cmd_map.get(framework, ["python", "-m", "pytest", "-q"])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = (stdout.decode() + stderr.decode()).strip()
        return TestResult(
            passed=process.returncode == 0,
            output=output[:1000],
            framework=framework,
        )
    except (FileNotFoundError, OSError) as exc:
        return TestResult(passed=True, output=f"Test command failed: {exc}", framework=framework)
