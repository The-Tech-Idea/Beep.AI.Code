"""Session switcher dialog (Ctrl+S)."""

from __future__ import annotations

from textual import events
from textual.screen import ModalScreen
from textual.widgets import Input, Static


class SessionSwitcher(ModalScreen):
    """Dialog for browsing and switching between sessions."""

    DEFAULT_CSS = """
    SessionSwitcher {
        align: center middle;
    }
    SessionSwitcher > .switcher-container {
        width: 60;
        height: 16;
        background: $surface;
        border: tall $primary;
        padding: 1;
    }
    SessionSwitcher Input {
        width: 100%;
        margin-bottom: 1;
    }
    SessionSwitcher #session-list {
        width: 100%;
        height: 1fr;
        overflow: auto;
    }
    SessionSwitcher .session-item {
        padding: 0 1;
    }
    SessionSwitcher .session-item--highlighted {
        background: $accent;
        color: $text;
    }
    SessionSwitcher .session-meta {
        color: $text-muted;
    }
    SessionSwitcher .session-current {
        color: $success;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("up", "navigate_up", "Up"),
        ("down", "navigate_down", "Down"),
        ("enter", "select", "Select"),
        ("ctrl+n", "new_session", "New"),
    ]

    def __init__(self, sessions: list[dict], current_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sessions = sessions
        self._current_id = current_id
        self._filtered: list[dict] = list(sessions)
        self._selected_index = 0

    def compose(self):
        yield Static("[bold]Sessions[/]", id="switcher-title")
        yield Input(id="search-input", placeholder="Search sessions...")
        yield Static(id="session-list")

    def on_mount(self) -> None:
        self._update_list()
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        if not query:
            self._filtered = list(self._sessions)
        else:
            self._filtered = [
                s
                for s in self._sessions
                if query in s.get("id", "").lower() or query in s.get("title", "").lower()
            ]
        self._selected_index = 0
        self._update_list()

    def _update_list(self) -> None:
        widget = self.query_one("#session-list", Static)
        if not self._filtered:
            widget.update("[dim]No sessions found[/]")
            return

        lines = []
        lines.append(f"  [session-current]▸ {self._current_id[:8]}[/] (current)")
        lines.append("")

        for i, session in enumerate(self._filtered):
            sid = session.get("id", "?")
            title = session.get("title", "Untitled")
            messages = session.get("message_count", 0)
            updated = session.get("updated_at", "")

            prefix = "  " if i == self._selected_index else "  "
            marker = "▸ " if i == self._selected_index else "  "

            line = f"{prefix}{marker}[session-item]{title}[/] "
            line += f"[session-meta]({sid[:8]}, {messages} msgs)[/]"
            if i == self._selected_index:
                line = f"[session-item--highlighted]{line}[/]"
            lines.append(line)

        lines.append("")
        lines.append("[dim]Ctrl+N: new session | Enter: switch | Esc: close[/]")
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
            session = self._filtered[self._selected_index]
            self.dismiss(session.get("id"))

    def action_new_session(self) -> None:
        self.dismiss("__new__")

    def action_close(self) -> None:
        self.dismiss(None)
