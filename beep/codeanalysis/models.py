"""Models for code analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from beep.codeindex.symbols import CodeSymbol


class AnalysisSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class AnalysisIssue:
    code: str
    message: str
    severity: Literal["info", "warning", "error"]
    file_path: str
    line: int | None = None
    column: int | None = None
    tool: str = "unknown"

    def summary(self) -> str:
        loc = f"{self.file_path}"
        if self.line:
            loc += f":{self.line}"
            if self.column:
                loc += f":{self.column}"
        return f"[{self.severity.upper()}] {loc} ({self.tool}) {self.message}"


@dataclass
class CodeAnalysisResult:
    symbols: list[CodeSymbol] = field(default_factory=list)
    issues: list[AnalysisIssue] = field(default_factory=list)
    dependencies: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_prompt_section(self) -> str:
        lines: list[str] = []
        if self.symbols:
            lines.append(
                f"Found {len(self.symbols)} symbols across {len(set(s.file_path for s in self.symbols))} files"
            )
        if self.issues:
            lines.append(
                f"Analysis found {len(self.issues)} issues ({self.error_count} errors, {self.warning_count} warnings):"
            )
            for issue in self.issues[:20]:
                lines.append(f"  {issue.summary()}")
            if len(self.issues) > 20:
                lines.append(f"  ... and {len(self.issues) - 20} more issues")
        if self.metrics:
            lines.append("Metrics:")
            for k, v in self.metrics.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)
