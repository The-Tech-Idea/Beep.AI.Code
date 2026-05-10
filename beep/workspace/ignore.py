""".beepignore file parser (gitignore-style patterns)."""

from __future__ import annotations

from pathlib import Path

import pathspec


class IgnoreMatcher:
    """Matches files against .beepignore patterns.

    Falls back to .gitignore if .beepignore doesn't exist.
    """

    DEFAULT_PATTERNS = [
        ".git/",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        ".env",
        "*.egg-info/",
        ".venv/",
        "venv/",
        "node_modules/",
        ".tox/",
        ".mypy_cache/",
        ".ruff_cache/",
        ".pytest_cache/",
        "dist/",
        "build/",
    ]

    def __init__(
        self,
        root: Path,
        patterns: list[str] | None = None,
    ) -> None:
        self._root = root.resolve()
        self._spec = self._load_spec(patterns)

    def _load_spec(self, custom_patterns: list[str] | None) -> pathspec.PathSpec:
        all_patterns = list(self.DEFAULT_PATTERNS)

        beepignore = self._root / ".beepignore"
        gitignore = self._root / ".gitignore"
        beep_dir_ignore = self._root / ".beep" / "ignore"

        if beepignore.exists():
            all_patterns.extend(beepignore.read_text().splitlines())
        elif gitignore.exists():
            all_patterns.extend(gitignore.read_text().splitlines())

        # Always load .beep/ignore if present (even alongside .beepignore)
        if beep_dir_ignore.exists():
            all_patterns.extend(beep_dir_ignore.read_text().splitlines())

        if custom_patterns:
            all_patterns.extend(custom_patterns)

        return pathspec.PathSpec.from_lines("gitignore", all_patterns)

    def is_ignored(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        try:
            relative = path.resolve().relative_to(self._root)
        except ValueError:
            return True

        return self._spec.match_file(str(relative))
