"""Status bar widget with mode indicator."""

from __future__ import annotations

from textual.widgets import Label, Static


class StatusBar(Static):
    """Status bar showing model, session, mode, and token info."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    StatusBar .mode-plan {
        color: $warning;
    }
    StatusBar .mode-build {
        color: $success;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = ""
        self._session_id = ""
        self._mode = "build"
        self._token_count = 0
        self._token_budget = 0

    def on_mount(self) -> None:
        self.update(self._render())

    @property
    def mode(self) -> str:
        return self._mode

    def set_model(self, model: str) -> None:
        self._model = model
        self.update(self._render())

    def set_session(self, session_id: str) -> None:
        self._session_id = session_id[:8]
        self.update(self._render())

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.update(self._render())

    def set_tokens(self, count: int, budget: int = 0) -> None:
        self._token_count = count
        self._token_budget = budget
        self.update(self._render())

    def _render(self) -> str:
        mode_class = "mode-plan" if self._mode == "plan" else "mode-build"
        mode_icon = "📋" if self._mode == "plan" else "🔨"
        token_str = ""
        if self._token_budget > 0:
            pct = int(100 * self._token_count / self._token_budget)
            token_str = f" | Tokens: {self._token_count}/{self._token_budget} ({pct}%)"
        elif self._token_count > 0:
            token_str = f" | Tokens: {self._token_count}"

        return (
            f"[{mode_class}]{mode_icon} {self._mode.upper()}[/] "
            f"| Model: {self._model} "
            f"| Session: {self._session_id}"
            f"{token_str} "
            f" | Ctrl+P commands | ? help"
        )
