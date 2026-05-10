"""Model selector dialog (Ctrl+O)."""

from __future__ import annotations

from textual import events
from textual.screen import ModalScreen
from textual.widgets import Input, Static


class ModelSelector(ModalScreen):
    """Dialog for selecting an LLM model."""

    DEFAULT_CSS = """
    ModelSelector {
        align: center middle;
    }
    ModelSelector > .selector-container {
        width: 60;
        height: 16;
        background: $surface;
        border: tall $primary;
        padding: 1;
    }
    ModelSelector Input {
        width: 100%;
        margin-bottom: 1;
    }
    ModelSelector #model-list {
        width: 100%;
        height: 1fr;
        overflow: auto;
    }
    ModelSelector .model-item {
        padding: 0 1;
    }
    ModelSelector .model-item--highlighted {
        background: $accent;
        color: $text;
    }
    ModelSelector .model-current {
        color: $success;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("up", "navigate_up", "Up"),
        ("down", "navigate_down", "Down"),
        ("enter", "select", "Select"),
    ]

    def __init__(self, models: list[str], current: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._models = models
        self._current = current
        self._filtered: list[str] = list(models)
        self._selected_index = 0

    def compose(self):
        yield Static("[bold]Select Model[/]", id="model-title")
        yield Input(id="search-input", placeholder="Search models...")
        yield Static(id="model-list")

    def on_mount(self) -> None:
        self._update_list()
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        if not query:
            self._filtered = list(self._models)
        else:
            self._filtered = [m for m in self._models if query in m.lower()]
        self._selected_index = 0
        self._update_list()

    def _update_list(self) -> None:
        widget = self.query_one("#model-list", Static)
        if not self._filtered:
            widget.update("[dim]No models match[/]")
            return

        lines = []
        for i, model in enumerate(self._filtered):
            marker = "▸ " if i == self._selected_index else "  "
            current_marker = " [model-current](current)[/]" if model == self._current else ""
            line = f"  {marker}[model-item]{model}[/]{current_marker}"
            if i == self._selected_index:
                line = f"[model-item--highlighted]{line}[/]"
            lines.append(line)
        lines.append("")
        lines.append("[dim]↑↓ navigate | Enter: select | Esc: close[/]")
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
            self.dismiss(self._filtered[self._selected_index])

    def action_close(self) -> None:
        self.dismiss(None)
