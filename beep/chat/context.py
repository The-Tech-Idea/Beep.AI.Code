"""Chat context manager: @file mentions, pinned files, context building."""

from __future__ import annotations

from pathlib import Path

from beep.workspace.detector import find_workspace_root
from beep.workspace.file_ops import read_file
from beep.workspace.ignore import IgnoreMatcher

MAX_FILE_SIZE = 50_000


class ChatContext:
    """Manages conversation context: pinned files, @mentions, memory."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._root = workspace_root or find_workspace_root()
        self._pinned: list[Path] = []
        self._matcher = IgnoreMatcher(self._root)

    @property
    def pinned_files(self) -> list[Path]:
        return list(self._pinned)

    def pin_file(self, path: Path) -> str:
        """Pin a file to always include in context."""
        resolved = self._resolve(path)
        if not resolved:
            return f"[red]File not found: {path}[/red]"
        if resolved in self._pinned:
            return f"[yellow]Already pinned: {resolved.name}[/yellow]"
        self._pinned.append(resolved)
        return f"[green]Pinned: {resolved.name}[/green]"

    def unpin_file(self, path: Path) -> str:
        """Unpin a file."""
        resolved = self._resolve(path)
        if resolved and resolved in self._pinned:
            self._pinned.remove(resolved)
            return f"[green]Unpinned: {resolved.name}[/green]"
        return f"[yellow]Not pinned: {path}[/yellow]"

    def build_context(self) -> str:
        """Build context string from pinned files."""
        if not self._pinned:
            return ""

        parts = ["## Pinned Files"]
        for p in self._pinned:
            if not p.exists() or p.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                content = read_file(p, show_numbers=True, highlight=False)
                parts.append(f"### {p.name}\n```\n{content}\n```")
            except (OSError, UnicodeDecodeError):
                pass

        return "\n\n".join(parts)

    def resolve_mentions(self, text: str) -> tuple[str, list[str]]:
        """Resolve @file mentions in text.

        Returns (cleaned_text, list_of_included_files).
        """
        import re

        included = []
        parts = []

        segments = re.split(r"(@\S+)", text)
        for segment in segments:
            if segment.startswith("@"):
                file_path = segment[1:]
                resolved = self._resolve(Path(file_path))
                if resolved and resolved.exists():
                    try:
                        content = read_file(
                            resolved, show_numbers=True, highlight=False
                        )
                        included.append(resolved.name)
                        parts.append(f"## {resolved.name}\n```\n{content}\n```")
                    except (OSError, UnicodeDecodeError):
                        parts.append(f"[red]Could not read: {file_path}[/red]")
                else:
                    parts.append(f"[yellow]File not found: {file_path}[/yellow]")
            else:
                parts.append(segment)

        cleaned = "".join(parts)
        return cleaned, included

    def _resolve(self, path: Path) -> Path | None:
        """Resolve a file path relative to workspace root."""
        if path.is_absolute() and path.exists():
            return path
        candidate = self._root / path
        if candidate.exists():
            return candidate.resolve()
        return None
