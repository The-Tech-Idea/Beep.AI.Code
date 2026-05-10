"""Rollback manager for safe file restoration."""

from __future__ import annotations

from pathlib import Path


class RollbackManager:
    """Handles file restoration with safety checks."""

    def can_rollback(self, path: Path) -> bool:
        """Check if a file can be safely restored."""
        if not path.exists():
            return False
        protected = {".git", ".env", "secrets.json", "id_rsa", "id_ed25519"}
        parts = {p.name for p in path.parts}
        return not bool(parts & protected)

    def restore(self, path: Path, content: str) -> None:
        """Write original content back to the file."""
        path.write_text(content, encoding="utf-8")
