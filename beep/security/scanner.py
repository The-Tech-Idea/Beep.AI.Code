"""Security vulnerability scanning.

Detects common security issues in code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.table import Table



from beep.utils.console import get_console
class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    """A security finding."""

    file: str
    line: int
    severity: Severity
    rule: str
    message: str
    suggestion: str = ""


# Python security patterns
PYTHON_PATTERNS = [
    {
        "pattern": r"eval\s*\(",
        "severity": Severity.CRITICAL,
        "rule": "python-eval",
        "message": "Use of eval() - arbitrary code execution risk",
        "suggestion": "Use ast.literal_eval() or json.loads() instead",
    },
    {
        "pattern": r"exec\s*\(",
        "severity": Severity.CRITICAL,
        "rule": "python-exec",
        "message": "Use of exec() - arbitrary code execution risk",
        "suggestion": "Avoid exec() with untrusted input",
    },
    {
        "pattern": r"os\.system\s*\(",
        "severity": Severity.HIGH,
        "rule": "python-os-system",
        "message": "os.system() - shell injection risk",
        "suggestion": "Use subprocess.run() with list args instead",
    },
    {
        "pattern": r"subprocess\..*shell\s*=\s*True",
        "severity": Severity.HIGH,
        "rule": "python-subprocess-shell",
        "message": "subprocess with shell=True - shell injection risk",
        "suggestion": "Use shell=False with list arguments",
    },
    {
        "pattern": r"pickle\.loads?\s*\(",
        "severity": Severity.HIGH,
        "rule": "python-pickle",
        "message": "pickle.loads() - deserialization vulnerability",
        "suggestion": "Use json or msgpack for untrusted data",
    },
    {
        "pattern": r"yaml\.load\s*\([^)]*\)(?!.*Loader)",
        "severity": Severity.HIGH,
        "rule": "python-yaml-load",
        "message": "yaml.load() without safe Loader",
        "suggestion": "Use yaml.safe_load() instead",
    },
    {
        "pattern": r"requests\..*verify\s*=\s*False",
        "severity": Severity.HIGH,
        "rule": "python-ssl-verify",
        "message": "SSL verification disabled",
        "suggestion": "Always verify SSL certificates",
    },
    {
        "pattern": r"hashlib\.md5\s*\(",
        "severity": Severity.MEDIUM,
        "rule": "python-md5",
        "message": "MD5 hash - cryptographically broken",
        "suggestion": "Use SHA-256 or SHA-3",
    },
    {
        "pattern": r"password\s*=\s*[\"'][^\"']+[\"']",
        "severity": Severity.HIGH,
        "rule": "python-hardcoded-password",
        "message": "Hardcoded password detected",
        "suggestion": "Use environment variables or a secrets manager",
    },
    {
        "pattern": r"api[_-]?key\s*=\s*[\"'][^\"']+[\"']",
        "severity": Severity.HIGH,
        "rule": "python-hardcoded-apikey",
        "message": "Hardcoded API key detected",
        "suggestion": "Use environment variables",
    },
]

# JavaScript security patterns
JS_PATTERNS = [
    {
        "pattern": r"eval\s*\(",
        "severity": Severity.CRITICAL,
        "rule": "js-eval",
        "message": "Use of eval() - XSS risk",
        "suggestion": "Use JSON.parse() or Function constructor carefully",
    },
    {
        "pattern": r"innerHTML\s*=",
        "severity": Severity.HIGH,
        "rule": "js-innerhtml",
        "message": "innerHTML assignment - XSS risk",
        "suggestion": "Use textContent or DOMPurify.sanitize()",
    },
    {
        "pattern": r"document\.write\s*\(",
        "severity": Severity.HIGH,
        "rule": "js-document-write",
        "message": "document.write() - XSS risk",
        "suggestion": "Use DOM manipulation methods",
    },
    {
        "pattern": r"setTimeout\s*\(\s*[\"']",
        "severity": Severity.MEDIUM,
        "rule": "js-settimeout-string",
        "message": "setTimeout with string - eval-like behavior",
        "suggestion": "Pass a function instead of a string",
    },
    {
        "pattern": r"password\s*[:=]\s*[\"'][^\"']+[\"']",
        "severity": Severity.HIGH,
        "rule": "js-hardcoded-password",
        "message": "Hardcoded password detected",
        "suggestion": "Use environment variables",
    },
]


def scan_file(path: Path) -> list[Finding]:
    """Scan a file for security issues."""
    ext = path.suffix.lower()
    patterns = []

    if ext == ".py":
        patterns = PYTHON_PATTERNS
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        patterns = JS_PATTERNS
    else:
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    findings = []
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue

        for p in patterns:
            if re.search(p["pattern"], line):
                findings.append(Finding(
                    file=str(path),
                    line=i,
                    severity=p["severity"],
                    rule=p["rule"],
                    message=p["message"],
                    suggestion=p.get("suggestion", ""),
                ))

    return findings


def scan_directory(
    root: Path,
    max_files: int = 200,
) -> list[Finding]:
    """Scan directory for security issues."""
    from beep.workspace.ignore import IgnoreMatcher

    matcher = IgnoreMatcher(root)
    findings = []
    count = 0

    for path in root.rglob("*"):
        if count >= max_files:
            break
        if not path.is_file() or matcher.is_ignored(path):
            continue
        if path.suffix.lower() in (".py", ".js", ".ts", ".jsx", ".tsx"):
            findings.extend(scan_file(path))
            count += 1

    return findings


def display_findings(findings: list[Finding]) -> None:
    """Display security findings."""
    if not findings:
        get_console().print("[green]No security issues found[/green]")
        return

    severity_counts = {s: 0 for s in Severity}
    for f in findings:
        severity_counts[f.severity] += 1

    summary = " | ".join(
        f"[{'red' if s in (Severity.CRITICAL, Severity.HIGH) else 'yellow'}]{v} {s.value}[/]"
        for s, v in severity_counts.items()
        if v > 0
    )
    get_console().print(f"[bold]Security Scan Results:[/bold] {summary}\n")

    table = Table(title="Findings")
    table.add_column("Severity", style="bold")
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right")
    table.add_column("Rule")
    table.add_column("Message")

    severity_colors = {
        Severity.CRITICAL: "red",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "blue",
        Severity.INFO: "dim",
    }

    for f in sorted(findings, key=lambda x: x.severity.value):
        color = severity_colors.get(f.severity, "white")
        table.add_row(
            f"[{color}]{f.severity.value.upper()}[/{color}]",
            f.file,
            str(f.line),
            f.rule,
            f.message,
        )

    get_console().print(table)
