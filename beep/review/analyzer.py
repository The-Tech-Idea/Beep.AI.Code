"""Code review and diff analysis.

Provides:
- Review staged/unstaged changes
- Review specific files
- PR-ready review summaries
- Security and quality checks
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from beep.workspace.git import get_git_diff, get_git_diff_for_file



from beep.utils.console import get_console
class ReviewSeverity(Enum):
    """Severity of a review finding."""

    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"


@dataclass
class ReviewFinding:
    """A single review finding."""

    file: str
    line: int
    severity: ReviewSeverity
    message: str
    suggestion: str = ""


@dataclass
class ReviewResult:
    """Result of a code review."""

    findings: list[ReviewFinding]
    summary: str = ""
    files_reviewed: int = 0
    total_issues: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ReviewSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ReviewSeverity.WARNING)

    @property
    def is_clean(self) -> bool:
        return self.critical_count == 0 and self.warning_count == 0


REVIEW_PROMPT = """You are an expert code reviewer. Review the following diff for:

1. **Bugs**: Logic errors, edge cases, race conditions
2. **Security**: Injection, XSS, auth bypass, data exposure
3. **Performance**: N+1 queries, memory leaks, inefficient algorithms
4. **Style**: Naming, formatting, consistency
5. **Best Practices**: SOLID, DRY, error handling

For each issue found, provide:
- File and line number
- Severity (critical/warning/suggestion)
- Description of the issue
- Suggested fix

Format your response as a structured review."""


def get_diff_to_review(
    workspace_root: Path,
    staged: bool = True,
    file_path: str | None = None,
) -> str | None:
    """Get the diff content to review."""
    if file_path:
        return get_git_diff_for_file(workspace_root, file_path)

    if staged:
        from beep.workspace.git_ext.operations import run_git
        success, out, _ = run_git(["diff", "--cached"], workspace_root)
        if success and out:
            return out

    diff = get_git_diff(workspace_root, staged=False)
    if diff:
        return diff

    return None


def display_review_result(result: ReviewResult) -> None:
    """Display review results with Rich formatting."""
    status = "[green]CLEAN[/green]" if result.is_clean else "[red]ISSUES FOUND[/red]"

    get_console().print(Panel(
        f"[bold]Files reviewed:[/bold] {result.files_reviewed}\n"
        f"[bold]Critical:[/bold] {result.critical_count}\n"
        f"[bold]Warnings:[/bold] {result.warning_count}\n"
        f"[bold]Total issues:[/bold] {result.total_issues}\n"
        f"[bold]Status:[/bold] {status}\n\n"
        f"{result.summary}",
        title="Code Review",
        border_style="green" if result.is_clean else "red",
    ))

    if result.findings:
        table = Table(title="Findings")
        table.add_column("Severity", style="bold")
        table.add_column("File", style="cyan")
        table.add_column("Line", justify="right")
        table.add_column("Issue")
        table.add_column("Suggestion", style="dim")

        severity_colors = {
            ReviewSeverity.CRITICAL: "red",
            ReviewSeverity.WARNING: "yellow",
            ReviewSeverity.SUGGESTION: "blue",
            ReviewSeverity.INFO: "dim",
        }

        for finding in result.findings:
            color = severity_colors.get(finding.severity, "white")
            table.add_row(
                f"[{color}]{finding.severity.value.upper()}[/{color}]",
                finding.file,
                str(finding.line),
                finding.message[:60],
                finding.suggestion[:40],
            )

        get_console().print(table)
