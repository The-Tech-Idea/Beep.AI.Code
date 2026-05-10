"""Validation policy and validator for agent task completion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationPolicy:
    """Rules for validating agent work after edits."""

    run_tests_after_edit: bool = True
    run_lint_after_edit: bool = False
    run_typecheck_after_edit: bool = False
    max_repair_attempts: int = 3
    required_commands: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Outcome of a validation step."""

    step: str
    success: bool
    output: str = ""
    error: str = ""
    command: str = ""


@dataclass
class ValidationReport:
    """Aggregated validation results for a completed task."""

    results: list[ValidationResult] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.success for r in self.results) if self.results else True

    def add(self, result: ValidationResult) -> None:
        self.results.append(result)

    def summary(self) -> str:
        lines: list[str] = []
        if self.changed_files:
            lines.append("Changed files:")
            for f in self.changed_files:
                lines.append(f"  - {f}")
        lines.append("")
        lines.append("Validation:")
        if not self.results:
            lines.append("  No validation steps configured.")
        else:
            for r in self.results:
                status = "PASSED" if r.success else "FAILED"
                lines.append(f"  [{status}] {r.step}")
                if r.error:
                    lines.append(f"    {r.error[:200]}")
        return "\n".join(lines)


class Validator:
    """Runs validation steps against the workspace."""

    def __init__(self, policy: ValidationPolicy) -> None:
        self.policy = policy

    def should_run(self, step: str) -> bool:
        """Check if a validation step is enabled."""
        if step == "tests":
            return self.policy.run_tests_after_edit
        if step == "lint":
            return self.policy.run_lint_after_edit
        if step == "typecheck":
            return self.policy.run_typecheck_after_edit
        if step in self.policy.required_commands:
            return True
        return False
