"""File operations: read, write, edit, diff."""

from __future__ import annotations

import difflib
import shutil
from datetime import datetime
from pathlib import Path

from rich.panel import Panel

from beep.chat.code_blocks import highlight_file



from beep.utils.console import get_console
def read_file(
    path: Path,
    *,
    start_line: int | None = None,
    end_line: int | None = None,
    show_numbers: bool = True,
    highlight: bool = True,
) -> str:
    """Read a file with optional line range.

    Args:
        path: File path
        start_line: First line to show (1-indexed)
        end_line: Last line to show (1-indexed)
        show_numbers: Show line numbers
        highlight: Apply syntax highlighting

    Returns:
        Formatted file content
    """
    lines, _total_lines = read_lines(path, start=start_line, end=end_line)

    if show_numbers:
        offset = start_line or 1
        numbered = []
        for i, line in enumerate(lines):
            numbered.append(f"{offset + i:4d} | {line}")
        output = "\n".join(numbered)
    else:
        output = "\n".join(lines)

    if highlight:
        return highlight_file(output, path.name)
    return output


def write_file(
    path: Path,
    content: str,
    *,
    create_backup: bool = True,
) -> Path:
    """Write content to a file.

    Args:
        path: File path
        content: Content to write
        create_backup: Create .backup file before writing

    Returns:
        Path to the written file
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if create_backup and path.exists():
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = path.with_suffix(path.suffix + f".backup.{ts}")
        shutil.copy2(path, backup)

    path.write_text(content, encoding="utf-8")
    return path


def create_diff(old_content: str, new_content: str, path: str = "file") -> str:
    """Create a unified diff between two content strings.

    Args:
        old_content: Original content
        new_content: New content
        path: File path for diff header

    Returns:
        Unified diff string
    """
    diff = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    return "\n".join(diff)


def read_lines(
    path: Path,
    start: int | None = None,
    end: int | None = None,
) -> tuple[list[str], int]:
    """Read lines from a file with optional range.

    Args:
        path: File path
        start: First line to return, 1-indexed (None = from beginning)
        end: Last line to return, 1-indexed inclusive (None = to end)

    Returns:
        (lines, total_line_count)
    """
    all_lines = path.read_text(encoding="utf-8").splitlines()
    total = len(all_lines)
    s = (start - 1) if start else 0
    e = end if end else total
    return all_lines[s:e], total


def show_diff(old_content: str, new_content: str, path: str = "file") -> None:
    """Display a diff with Rich formatting."""
    diff = create_diff(old_content, new_content, path)

    if not diff.strip():
        get_console().print("[yellow]No changes[/yellow]")
        return

    get_console().print(Panel(diff, title=f"Diff: {path}", border_style="yellow", padding=(1, 2)))


def apply_edit(
    path: Path,
    old_content: str,
    new_content: str,
    *,
    require_confirm: bool = True,
) -> bool:
    """Apply an edit with optional confirmation.

    Args:
        path: File to edit
        old_content: Current content
        new_content: New content
        require_confirm: Ask for confirmation

    Returns:
        True if edit was applied
    """
    if old_content == new_content:
        get_console().print("[yellow]No changes to apply[/yellow]")
        return False

    show_diff(old_content, new_content, str(path))

    if require_confirm:
        from rich.prompt import Confirm

        if not Confirm.ask("Apply changes?"):
            get_console().print("[yellow]Edit cancelled[/yellow]")
            return False

    write_file(path, new_content)
    get_console().print(f"[green]Updated {path}[/green]")
    return True
