"""Edit checkpoint timeline — capture file state before each edit for undo/restore."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class EditCheckpoint:
    file_path: Path
    original_content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    tool_name: str = ""


class CheckpointTimeline:
    """Linear edit history for undo/restore across a chat session."""

    MAX_CHECKPOINTS = 50

    def __init__(self) -> None:
        self._checkpoints: list[EditCheckpoint] = []

    def capture(self, file_path: Path, original_content: str, tool_name: str = "") -> None:
        self._checkpoints.append(
            EditCheckpoint(
                file_path=file_path.resolve(),
                original_content=original_content,
                tool_name=tool_name,
            )
        )
        if len(self._checkpoints) > self.MAX_CHECKPOINTS:
            self._checkpoints = self._checkpoints[-self.MAX_CHECKPOINTS :]

    def pop_last(self) -> EditCheckpoint | None:
        if not self._checkpoints:
            return None
        return self._checkpoints.pop()

    def restore_last(self) -> EditCheckpoint | None:
        checkpoint = self.pop_last()
        if checkpoint is None:
            return None
        if checkpoint.file_path.exists():
            path_parts = {p for p in checkpoint.file_path.parts}
            protected = {".git", ".env", "secrets.json", "id_rsa", "id_ed25519"}
            if not (path_parts & protected):
                checkpoint.file_path.write_text(checkpoint.original_content, encoding="utf-8")
        return checkpoint

    def list_checkpoints(self) -> list[dict[str, Any]]:
        return [
            {
                "index": i,
                "file": str(cp.file_path),
                "tool": cp.tool_name,
                "timestamp": cp.timestamp.isoformat(),
                "content_preview": cp.original_content[:80],
            }
            for i, cp in enumerate(self._checkpoints)
        ]

    def __len__(self) -> int:
        return len(self._checkpoints)
