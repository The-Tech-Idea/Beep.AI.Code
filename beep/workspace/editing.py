"""Shared workspace edit preparation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PreparedWorkspaceEdit:
    """Prepared edit payload shared by CLI and chat edit flows."""

    path: Path
    old_content: str
    new_content: str

    def to_undo_record(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "old": self.old_content,
            "new": self.new_content,
        }


def prepare_workspace_edit(path: str | Path, *, new_content: str) -> PreparedWorkspaceEdit:
    """Load the current file content and prepare a shared edit payload."""
    file_path = Path(path)
    old_content = ""
    if file_path.exists():
        try:
            old_content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"Error: {exc}") from exc

    return PreparedWorkspaceEdit(
        path=file_path,
        old_content=old_content,
        new_content=new_content,
    )