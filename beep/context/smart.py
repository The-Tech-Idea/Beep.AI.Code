"""Smart context builder with file awareness.

Automatically detects relevant files based on:
- Git changes (modified, staged, untracked)
- Import dependencies
- Recently accessed files
- File type relevance
"""

from __future__ import annotations

from pathlib import Path

from beep.context.builder import MAX_CONTEXT_FILES
from beep.context.builder import build_context as _build_context
from beep.memory.loader import ProjectMemory, load_project_memory
from beep.workspace.detector import find_workspace_root
from beep.workspace.git import get_git_status, is_git_repo
from beep.workspace.ignore import IgnoreMatcher


class SmartContextBuilder:
    """Builds context with intelligent file selection."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._root = workspace_root or find_workspace_root()
        self._matcher = IgnoreMatcher(self._root)
        self._memory = load_project_memory(self._root)
        self._recent_files: list[Path] = []

    @property
    def workspace_root(self) -> Path:
        return self._root

    @property
    def project_memory(self) -> ProjectMemory:
        return self._memory

    def track_file_access(self, path: Path) -> None:
        """Track a file as recently accessed."""
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:50]

    def get_relevant_files(
        self,
        query: str = "",
        max_files: int = MAX_CONTEXT_FILES,
    ) -> list[Path]:
        """Get files relevant to the current context.

        Priority:
        1. Git-modified files
        2. Recently accessed files
        3. Files matching query keywords
        """
        candidates: list[Path] = []

        for path in self._get_git_changed_files():
            if path not in candidates:
                candidates.append(path)

        for path in self._recent_files:
            if path not in candidates and path.exists():
                candidates.append(path)

        if query:
            for path in self._search_by_keywords(query):
                if path not in candidates:
                    candidates.append(path)

        return candidates[:max_files]

    def build_full_context(
        self,
        query: str = "",
        max_files: int = MAX_CONTEXT_FILES,
    ) -> str:
        """Build complete context including project memory and relevant files."""
        parts = []

        memory_prompt = self._memory.to_system_prompt()
        if memory_prompt:
            parts.append(memory_prompt)

        if is_git_repo(self._root):
            status = self._get_git_status_summary()
            if status:
                parts.append(f"## Git Status\n\n{status}")

        files = self.get_relevant_files(query, max_files)
        if files:
            file_context = _build_context(files, self._root)
            if file_context:
                parts.append(file_context)

        return "\n\n".join(parts)

    def _get_git_changed_files(self) -> list[Path]:
        """Get list of git-modified files."""
        status = get_git_status(self._root)
        if not status:
            return []

        files = []
        for line in status.splitlines():
            if len(line) > 3:
                file_path = line[3:].strip()
                full_path = self._root / file_path
                if full_path.exists() and not self._matcher.is_ignored(full_path):
                    files.append(full_path)
        return files

    def _get_git_status_summary(self) -> str:
        """Get a concise git status summary."""
        status = get_git_status(self._root)
        if not status:
            return ""

        lines = status.splitlines()[:10]
        return "\n".join(lines)

    def _search_by_keywords(self, query: str) -> list[Path]:
        """Find files matching query keywords in their name or path."""
        keywords = [k.lower() for k in query.split() if len(k) > 2]
        if not keywords:
            return []

        matches = []
        for path in self._root.rglob("*"):
            if not path.is_file() or self._matcher.is_ignored(path):
                continue

            name_lower = path.name.lower()
            if any(kw in name_lower for kw in keywords):
                matches.append(path)

            if len(matches) >= 20:
                break

        return matches


def select_context_files(
    query: str,
    workspace_root: Path | None = None,
    max_files: int = MAX_CONTEXT_FILES,
) -> list[Path]:
    """Return ranked file paths most relevant to *query*.

    Files are scored by extension relevance and keyword matches against
    the file name and its parent directory names.  The function is safe
    to call with an empty query — it falls back to git-changed and
    recently-touched files.

    Parameters
    ----------
    query:
        The user's request text used to rank files.
    workspace_root:
        Workspace root to search.  Auto-detected when ``None``.
    max_files:
        Upper bound on the number of paths returned.

    Returns
    -------
    list[Path]
        Up to *max_files* existing file paths, ordered from most to least
        relevant.
    """
    from beep.app_service import get_app_service

    builder = get_app_service().smart_context(workspace_root)
    return builder.get_relevant_files(query=query, max_files=max_files)
