"""Chat message rendering widget."""

from __future__ import annotations

from textual.widgets import Static


class MessageDisplay(Static):
    """Renders a single chat message with markdown-style formatting."""

    DEFAULT_CSS = """
    MessageDisplay {
        padding: 1 2;
        border-bottom: tall $surface;
    }
    MessageDisplay.user {
        background: $boost;
    }
    MessageDisplay.assistant {
        background: transparent;
    }
    MessageDisplay.system {
        color: $text-muted;
        text-style: italic;
        padding: 0 2;
    }
    MessageDisplay.error {
        color: $error;
    }
    """

    def __init__(self, role: str, content: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._role = role
        self._content = content
        self.add_class(role)

    @property
    def role(self) -> str:
        return self._role

    @property
    def content(self) -> str:
        return self._content

    def on_mount(self) -> None:
        self.update(self._render_message())

    def _render_message(self) -> str:
        if self._role == "system":
            return f"[italic dim]{self._content}[/]"
        if self._role == "error":
            return f"[bold red]Error:[/bold red] {self._content}"
        if self._role == "user":
            return self._format_user_message()
        if self._role == "assistant":
            return self._format_assistant_message()
        return self._content

    def _format_user_message(self) -> str:
        text = self._content
        text = self._highlight_code_blocks(text)
        text = self._highlight_inline_code(text)
        text = self._highlight_bash_commands(text)
        return f"[bold green]You:[/]\n{text}"

    def _format_assistant_message(self) -> str:
        text = self._content
        text = self._highlight_code_blocks(text)
        text = self._highlight_inline_code(text)
        return f"[bold blue]Assistant:[/]\n{text}"

    def _highlight_code_blocks(self, text: str) -> str:
        result = []
        parts = text.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1:
                lang = ""
                content = part
                if "\n" in part:
                    lang, content = part.split("\n", 1)
                result.append(f"\n[dim]{lang}\n[/dim][dim]{content}[/dim]\n")
            else:
                result.append(part)
        return "".join(result)

    def _highlight_inline_code(self, text: str) -> str:
        parts = text.split("`")
        result = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                result.append(f"[cyan]{part}[/]")
            else:
                result.append(part)
        return "".join(result)

    def _highlight_bash_commands(self, text: str) -> str:
        if text.startswith("!"):
            return f"[bold yellow]Shell:[/]\n{text[1:].strip()}"
        return text

    def update_content(self, content: str) -> None:
        self._content = content
        self.update(self._render_message())
