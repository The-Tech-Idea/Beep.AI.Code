"""Codebase analysis tools.

Provides:
- File statistics (lines, complexity)
- Dependency analysis
- Code quality metrics
- Architecture overview
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.table import Table

from beep.workspace.ignore import IgnoreMatcher



from beep.utils.console import get_console
@dataclass
class FileStats:
    """Statistics for a single file."""

    path: str
    lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0
    functions: int = 0
    classes: int = 0


@dataclass
class ProjectStats:
    """Aggregate project statistics."""

    total_files: int = 0
    total_lines: int = 0
    total_code_lines: int = 0
    total_blank_lines: int = 0
    total_comment_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    by_language: dict[str, int] = field(default_factory=dict)
    largest_files: list[FileStats] = field(default_factory=list)


LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".jsx": "JavaScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
}

COMMENT_PREFIXES = {
    ".py": "#",
    ".js": "//",
    ".ts": "//",
    ".go": "//",
    ".rs": "//",
    ".java": "//",
    ".cpp": "//",
    ".c": "//",
    ".cs": "//",
    ".rb": "#",
    ".php": "//",
    ".swift": "//",
    ".kt": "//",
    ".sh": "#",
    ".yaml": "#",
    ".yml": "#",
}

FUNCTION_PATTERNS = {
    ".py": ["def ", "async def "],
    ".js": ["function ", "const ", "=>"],
    ".ts": ["function ", "const ", "=>"],
    ".go": ["func "],
    ".rs": ["fn ", "async fn "],
    ".java": ["public ", "private ", "protected "],
}


def analyze_file(path: Path) -> FileStats | None:
    """Analyze a single file."""
    ext = path.suffix.lower()
    if ext not in LANGUAGE_EXTENSIONS:
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    lines = content.splitlines()
    stats = FileStats(
        path=str(path),
        lines=len(lines),
    )

    comment_prefix = COMMENT_PREFIXES.get(ext, "")
    func_patterns = FUNCTION_PATTERNS.get(ext, [])

    for line in lines:
        stripped = line.strip()
        if not stripped:
            stats.blank_lines += 1
        elif comment_prefix and stripped.startswith(comment_prefix):
            stats.comment_lines += 1
        else:
            stats.code_lines += 1

        for pattern in func_patterns:
            if stripped.startswith(pattern) and "(" in stripped:
                stats.functions += 1
                break

        if stripped.startswith("class "):
            stats.classes += 1

    return stats


def analyze_project(
    workspace_root: Path,
    max_files: int = 500,
) -> ProjectStats:
    """Analyze the entire project."""
    stats = ProjectStats()
    matcher = IgnoreMatcher(workspace_root)
    file_stats_list: list[FileStats] = []

    for path in workspace_root.rglob("*"):
        if not path.is_file() or matcher.is_ignored(path):
            continue

        file_stats = analyze_file(path)
        if not file_stats:
            continue

        file_stats_list.append(file_stats)
        stats.total_files += 1
        stats.total_lines += file_stats.lines
        stats.total_code_lines += file_stats.code_lines
        stats.total_blank_lines += file_stats.blank_lines
        stats.total_comment_lines += file_stats.comment_lines
        stats.total_functions += file_stats.functions
        stats.total_classes += file_stats.classes

        ext = path.suffix.lower()
        lang = LANGUAGE_EXTENSIONS.get(ext, "Other")
        stats.by_language[lang] = stats.by_language.get(lang, 0) + 1

        if len(file_stats_list) >= max_files:
            break

    stats.largest_files = sorted(
        file_stats_list, key=lambda f: f.lines, reverse=True
    )[:10]

    return stats


def display_project_stats(stats: ProjectStats) -> None:
    """Display project statistics."""
    get_console().print("[bold]Project Statistics[/bold]\n")

    get_console().print(f"Total files: {stats.total_files}")
    get_console().print(f"Total lines: {stats.total_lines}")
    get_console().print(f"Code lines: {stats.total_code_lines}")
    get_console().print(f"Blank lines: {stats.total_blank_lines}")
    get_console().print(f"Comment lines: {stats.total_comment_lines}")
    get_console().print(f"Functions: {stats.total_functions}")
    get_console().print(f"Classes: {stats.total_classes}")
    get_console().print()

    if stats.by_language:
        table = Table(title="Files by Language")
        table.add_column("Language", style="cyan")
        table.add_column("Files", justify="right")
        table.add_column("%", justify="right")

        for lang, count in sorted(
            stats.by_language.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / stats.total_files * 100) if stats.total_files else 0
            table.add_row(lang, str(count), f"{pct:.1f}%")

        get_console().print(table)

    if stats.largest_files:
        table = Table(title="Largest Files")
        table.add_column("File", style="cyan")
        table.add_column("Lines", justify="right")
        table.add_column("Functions", justify="right")

        for fs in stats.largest_files:
            table.add_row(fs.path, str(fs.lines), str(fs.functions))

        get_console().print(table)
