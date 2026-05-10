"""Verification runner for post-edit checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from beep.agent.verification.lint_runner import run_workspace_lint, LintResult
from beep.agent.verification.test_runner import run_workspace_tests, TestResult


@dataclass
class VerificationResult:
    """Combined result of post-edit verification."""

    tests: TestResult | None = None
    lint: LintResult | None = None
    files_checked: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        if self.tests and not self.tests.passed:
            return False
        if self.lint and not self.lint.passed:
            return False
        return True

    def to_message(self) -> str:
        lines = ["Verification results:"]
        if self.tests:
            lines.append(
                f"  Tests: {'PASS' if self.tests.passed else 'FAIL'} ({self.tests.output[:200]})"
            )
        else:
            lines.append("  Tests: skipped (no test framework detected)")
        if self.lint:
            lines.append(
                f"  Lint: {'PASS' if self.lint.passed else 'FAIL'} ({self.lint.output[:200]})"
            )
        else:
            lines.append("  Lint: skipped (no linter detected)")
        return "\n".join(lines)


class VerificationRunner:
    """Runs post-edit verification checks (tests + lint)."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    async def run(self, files_touched: list[str] | None = None) -> VerificationResult:
        """Run all verification checks."""
        tests = await run_workspace_tests(self._workspace_root)
        lint = await run_workspace_lint(self._workspace_root, files_touched)
        return VerificationResult(
            tests=tests,
            lint=lint,
            files_checked=files_touched or [],
        )
