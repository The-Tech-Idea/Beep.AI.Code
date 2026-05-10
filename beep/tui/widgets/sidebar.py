"""Sidebar widget showing session info and file changes."""

from __future__ import annotations

from pathlib import Path

from textual.containers import ScrollableContainer
from textual.widgets import Static


class SessionSidebar(ScrollableContainer):
    """Sidebar showing session title, modified files, and context."""

    DEFAULT_CSS = """
    SessionSidebar {
        width: 35;
        dock: right;
        background: $surface-darken-1;
        border-left: tall $border;
        padding: 0 1;
        overflow: auto;
    }
    SessionSidebar .sidebar-header {
        text-style: bold;
        color: $primary;
        padding: 1 0 0 0;
    }
    SessionSidebar .file-item {
        padding: 0 0 0 2;
    }
    SessionSidebar .section-title {
        text-style: bold underline;
        padding: 1 0 0 0;
    }
    SessionSidebar .empty {
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = ""
        self._modified_files: list[str] = []
        self._tool_calls: list[tuple[str, str]] = []

    def on_mount(self) -> None:
        self.update(self._render())

    def set_title(self, title: str) -> None:
        self._title = title
        self.update(self._render())

    def add_modified_file(self, path: str) -> None:
        if path not in self._modified_files:
            self._modified_files.append(path)
            self.update(self._render())

    def add_tool_call(self, tool_name: str, status: str) -> None:
        self._tool_calls.append((tool_name, status))
        self.update(self._render())

    def _render(self) -> str:
        lines = []
        lines.append("[sidebar-header]Session[/]")
        if self._title:
            lines.append(f"  {self._title}")
        else:
            lines.append("  [empty]New session[/]")

        lines.append("[section-title]Files Modified[/]")
        if self._modified_files:
            for f in self._modified_files:
                lines.append(f"  [file-item]✎ {f}[/]")
        else:
            lines.append("  [empty]No changes yet[/]")

        lines.append("[section-title]Tool Calls[/]")
        if self._tool_calls:
            for name, status in self._tool_calls:
                icon = "⏳" if status == "running" else "✓"
                lines.append(f"  [file-item]{icon} {name}[/]")
        else:
            lines.append("  [empty]No tools used[/]")

        return "\n".join(lines)
