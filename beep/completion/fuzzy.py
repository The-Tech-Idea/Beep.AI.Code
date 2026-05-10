"""Fuzzy file picker (Ctrl+P style)."""

from __future__ import annotations

from pathlib import Path

from rich.prompt import Prompt
from rich.table import Table

from beep.workspace.detector import find_workspace_root
from beep.workspace.ignore import IgnoreMatcher


from beep.utils.console import get_console
MAX_RESULTS = 15


def fuzzy_score(query: str, text: str) -> int:
    """Score how well query matches text (higher = better)."""
    query = query.lower()
    text = text.lower()

    if not query:
        return 0

    score = 0
    qi = 0
    prev_match = False

    for i, c in enumerate(text):
        if qi < len(query) and c == query[qi]:
            if i == 0 or text[i - 1] in ("/", "_", "-", "."):
                score += 10
            elif prev_match:
                score += 5
            else:
                score += 1
            qi += 1
            prev_match = True
        else:
            prev_match = False

    return score if qi == len(query) else 0


def find_files(workspace_root: Path, max_files: int = 500) -> list[Path]:
    """Find all files in workspace."""
    matcher = IgnoreMatcher(workspace_root)
    files = []

    for path in workspace_root.rglob("*"):
        if matcher.is_ignored(path):
            continue
        if path.is_file():
            files.append(path)
        if len(files) >= max_files:
            break

    return files


def pick_file(
    workspace_root: Path | None = None,
    prompt_text: str = "Search files",
) -> Path | None:
    """Interactive fuzzy file picker.

    Returns selected file path or None.
    """
    root = workspace_root or find_workspace_root()
    files = find_files(root)

    get_console().print(f"[dim]{len(files)} files[/dim]")
    query = Prompt.ask(f"[bold]{prompt_text}[/bold]")

    if not query:
        return None

    scored = []
    for f in files:
        rel = str(f.relative_to(root))
        s = fuzzy_score(query, rel)
        if s > 0:
            scored.append((s, f, rel))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = scored[:MAX_RESULTS]

    if not results:
        get_console().print("[yellow]No matches[/yellow]")
        return None

    if len(results) == 1:
        return results[0][1]

    table = Table(title=f"Results for '{query}'")
    table.add_column("#", justify="right", style="dim")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right", style="dim")

    for i, (score, f, rel) in enumerate(results, 1):
        table.add_row(str(i), rel, str(score))

    get_console().print(table)

    choice = Prompt.ask("Select file (number)", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            return results[idx][1]
    except ValueError:
        pass

    return None
