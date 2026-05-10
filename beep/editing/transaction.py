"""Edit transaction system for safe file modifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from beep.editing.diff import generate_diff


@dataclass
class FileSnapshot:
    """Point-in-time copy of a file for rollback."""

    path: Path
    original: str


@dataclass
class EditRecord:
    """Record of a single file edit."""

    path: Path
    original: str
    new_content: str
    diff: str


class EditTransaction:
    """Transactional file editing with snapshot, diff, and rollback."""

    def __init__(self) -> None:
        self._snapshots: dict[Path, FileSnapshot] = {}
        self._records: list[EditRecord] = []
        from beep.app_service import get_app_service

        self._rollback = get_app_service().rollback

    def snapshot(self, path: Path) -> None:
        """Capture the current state of a file if not already snapshotted."""
        if path not in self._snapshots and path.exists():
            self._snapshots[path] = FileSnapshot(
                path=path,
                original=path.read_text(encoding="utf-8"),
            )

    def write_text(self, path: Path, content: str) -> EditRecord:
        """Write content to a file, recording the edit."""
        self.snapshot(path)
        original = self._snapshots[path].original if path in self._snapshots else ""
        diff = generate_diff(original, content, str(path))
        path.write_text(content, encoding="utf-8")
        record = EditRecord(
            path=path,
            original=original,
            new_content=content,
            diff=diff,
        )
        self._records.append(record)
        return record

    def rollback(self) -> list[Path]:
        """Restore all snapshotted files to their original state."""
        restored = []
        for snap in self._snapshots.values():
            if self._rollback.can_rollback(snap.path):
                self._rollback.restore(snap.path, snap.original)
                restored.append(snap.path)
        return restored

    def rollback_single(self, path: Path) -> bool:
        """Restore a single file to its pre-edit state."""
        if path in self._snapshots:
            snap = self._snapshots[path]
            if self._rollback.can_rollback(snap.path):
                self._rollback.restore(snap.path, snap.original)
                return True
        return False

    @property
    def changed_files(self) -> list[Path]:
        return [r.path for r in self._records]

    @property
    def summary(self) -> str:
        if not self._records:
            return "No files changed."
        lines = ["Changed files:"]
        for r in self._records:
            lines.append(f"  - {r.path}")
        return "\n".join(lines)

    @property
    def full_diff(self) -> str:
        return "\n\n".join(r.diff for r in self._records) if self._records else ""
