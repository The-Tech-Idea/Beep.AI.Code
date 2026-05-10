"""File picker dialog (Ctrl+F)."""

from __future__ import annotations

from pathlib import Path

from textual import events
from textual.screen import ModalScreen
from textual.widgets import Input, Static


class FilePicker(ModalScreen):
    """Fuzzy file picker for referencing files in messages."""

    DEFAULT_CSS = """
    FilePicker {
        align: center middle;
    }
    FilePicker > .picker-container {
        width: 70;
        height: 20;
        background: $surface;
        border: tall $primary;
        padding: 1;
    }
    FilePicker Input {
        width: 100%;
        margin-bottom: 1;
    }
    FilePicker #file-list {
        width: 100%;
        height: 1fr;
        overflow: auto;
    }
    FilePicker .file-item {
        padding: 0 1;
    }
    FilePicker .file-item--highlighted {
        background: $accent;
        color: $text;
    }
    FilePicker .file-dir {
        color: $primary;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("up", "navigate_up", "Up"),
        ("down", "navigate_down", "Down"),
        ("enter", "select", "Select"),
    ]

    def __init__(
        self,
        workspace_root: Path,
        max_select: int = 5,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._workspace_root = workspace_root
        self._max_select = max_select
        self._files: list[str] = []
        self._filtered: list[str] = []
        self._selected_index = 0
        self._selected: list[str] = []

    def on_mount(self) -> None:
        self._scan_files()
        self._filtered = list(self._files)
        self._update_list()
        self.query_one("#search-input", Input).focus()

    def _scan_files(self) -> None:
        if not self._workspace_root.exists():
            return
        for f in self._workspace_root.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                rel = f.relative_to(self._workspace_root)
                rel_str = str(rel).replace("\\", "/")
                if not any(
                    part.startswith(".")
                    or part in ("node_modules", "__pycache__", ".git", "venv", ".venv")
                    for part in rel.parts
                ):
                    self._files.append(rel_str)
        self._files.sort()

    def compose(self):
        yield Static("[bold]File Picker[/]", id="picker-title")
        yield Input(id="search-input", placeholder="Search files...")
        yield Static(id="file-list")

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        if not query:
            self._filtered = list(self._files)
        else:
            self._filtered = [f for f in self._files if query in f.lower()]
        self._selected_index = 0
        self._update_list()

    def _update_list(self) -> None:
        widget = self.query_one("#file-list", Static)
        if not self._filtered:
            widget.update("[dim]No files match[/]")
            return

        lines = []
        if self._selected:
            lines.append(f"[file-dir]Selected: {', '.join(self._selected)}[/]")
            lines.append("")

        for i, filepath in enumerate(self._filtered):
            marker = "▸ " if i == self._selected_index else "  "
            parts = filepath.rsplit("/", 1)
            if len(parts) == 2:
                dir_part, name_part = parts
                display = f"[file-dir]{dir_part}/[/]{name_part}"
            else:
                display = filepath
            line = f"{marker}[file-item]{display}[/]"
            if i == self._selected_index:
                line = f"[file-item--highlighted]{line}[/]"
            lines.append(line)

        lines.append("")
        lines.append(f"[dim]↑↓ navigate | Enter: select (max {self._max_select}) | Esc: close[/]")
        widget.update("\n".join(lines))

    def action_navigate_up(self) -> None:
        if self._selected_index > 0:
            self._selected_index -= 1
            self._update_list()

    def action_navigate_down(self) -> None:
        if self._selected_index < len(self._filtered) - 1:
            self._selected_index += 1
            self._update_list()

    def action_select(self) -> None:
        if self._filtered and self._selected_index < len(self._filtered):
            filepath = self._filtered[self._selected_index]
            if filepath not in self._selected and len(self._selected) < self._max_select:
                self._selected.append(filepath)
                self._update_list()
            if len(self._selected) >= self._max_select:
                self.dismiss(self._selected)

    def action_close(self) -> None:
        self.dismiss(self._selected if self._selected else None)
