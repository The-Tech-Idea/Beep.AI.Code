"""Bookmarks for frequently used files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

BOOKMARKS_FILE = Path.home() / ".beepai" / "bookmarks.json"


@dataclass
class Bookmark:
    """A file bookmark."""

    name: str
    path: str
    access_count: int = 0


@dataclass
class BookmarkManager:
    """Manages file bookmarks."""

    bookmarks: list[Bookmark] = field(default_factory=list)

    @classmethod
    def load(cls) -> BookmarkManager:
        """Load bookmarks from file."""
        if not BOOKMARKS_FILE.exists():
            return cls()

        try:
            data = json.loads(BOOKMARKS_FILE.read_text(encoding="utf-8"))
            bookmarks = [Bookmark(**b) for b in data.get("bookmarks", [])]
            return cls(bookmarks=bookmarks)
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self) -> None:
        """Save bookmarks to file."""
        BOOKMARKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "bookmarks": [
                {"name": b.name, "path": b.path, "access_count": b.access_count}
                for b in self.bookmarks
            ]
        }
        BOOKMARKS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add(self, name: str, path: Path) -> str:
        """Add or update a bookmark."""
        for b in self.bookmarks:
            if b.name == name:
                b.path = str(path)
                b.access_count += 1
                self.save()
                return f"[green]Updated bookmark: {name}[/green]"

        self.bookmarks.append(Bookmark(name=name, path=str(path), access_count=1))
        self.save()
        return f"[green]Bookmarked: {name} -> {path.name}[/green]"

    def remove(self, name: str) -> str:
        """Remove a bookmark."""
        self.bookmarks = [b for b in self.bookmarks if b.name != name]
        self.save()
        return f"[green]Removed bookmark: {name}[/green]"

    def get(self, name: str) -> Path | None:
        """Get bookmarked file path."""
        for b in self.bookmarks:
            if b.name == name:
                b.access_count += 1
                self.save()
                return Path(b.path)
        return None

    def list_all(self) -> list[Bookmark]:
        """List all bookmarks sorted by access count."""
        return sorted(self.bookmarks, key=lambda b: b.access_count, reverse=True)
