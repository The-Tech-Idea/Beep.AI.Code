"""Command palette dialog (Ctrl+P)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from textual import events
from textual.screen import ModalScreen
from textual.widgets import Input, Static


@dataclass
class CommandEntry:
    """A single command in the palette."""

    name: str
    description: str
    shortcut: str = ""
    callback: Callable | None = None


class CommandPalette(ModalScreen):
    """Fuzzy-searchable command palette."""

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
    }
    CommandPalette > .palette-container {
        width: 60;
        height: 20;
        background: $surface;
        border: tall $primary;
        padding: 1;
    }
    CommandPalette Input {
        width: 100%;
        margin-bottom: 1;
    }
    CommandPalette #command-list {
        width: 100%;
        height: 1fr;
        overflow: auto;
    }
    CommandPalette .cmd-item {
        padding: 0 1;
    }
    CommandPalette .cmd-item--highlighted {
        background: $accent;
        color: $text;
    }
    CommandPalette .cmd-shortcut {
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("up", "navigate_up", "Up"),
        ("down", "navigate_down", "Down"),
        ("enter", "select", "Select"),
    ]

    def __init__(self, commands: list[CommandEntry], **kwargs) -> None:
        super().__init__(**kwargs)
        self._commands = commands
        self._filtered: list[CommandEntry] = list(commands)
        self._selected_index = 0

    def compose(self):
        yield Static("[bold]Command Palette[/]", id="palette-title")
        yield Input(id="search-input", placeholder="Type to search commands...")
        yield Static(id="command-list")

    def on_mount(self) -> None:
        self._update_list()
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        if not query:
            self._filtered = list(self._commands)
        else:
            self._filtered = [
                cmd
                for cmd in self._commands
                if query in cmd.name.lower() or query in cmd.description.lower()
            ]
        self._selected_index = 0
        self._update_list()

    def _update_list(self) -> None:
        widget = self.query_one("#command-list", Static)
        if not self._filtered:
            widget.update("[dim]No commands match your search[/]")
            return

        lines = []
        for i, cmd in enumerate(self._filtered):
            prefix = "▸ " if i == self._selected_index else "  "
            shortcut = f"[cmd-shortcut]{cmd.shortcut}[/]" if cmd.shortcut else ""
            line = f"{prefix}[cmd-item]{cmd.name}[/] - {cmd.description} {shortcut}"
            if i == self._selected_index:
                line = f"[cmd-item--highlighted]{line}[/]"
            lines.append(line)
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
            cmd = self._filtered[self._selected_index]
            self.dismiss(cmd)

    def action_close(self) -> None:
        self.dismiss(None)
