"""Tool call visualization widget."""

from __future__ import annotations

from textual.containers import Container
from textual.widgets import Collapsible, Label, Static


class ToolCallDisplay(Static):
    """Displays a tool call with its status and output."""

    DEFAULT_CSS = """
    ToolCallDisplay {
        padding: 0 2 0 4;
        border-left: wide $primary;
        margin: 1 0;
    }
    ToolCallDisplay.running {
        border-left: wide $warning;
    }
    ToolCallDisplay.completed {
        border-left: wide $success;
    }
    ToolCallDisplay.failed {
        border-left: wide $error;
    }
    ToolCallDisplay .tool-name {
        text-style: bold;
    }
    ToolCallDisplay .tool-args {
        color: $text-muted;
    }
    """

    def __init__(
        self,
        tool_name: str,
        arguments: str = "",
        status: str = "running",
        output: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._tool_name = tool_name
        self._arguments = arguments
        self._status = status
        self._output = output
        self.add_class(status)

    def on_mount(self) -> None:
        self.update(self._render())

    def _render(self) -> str:
        icons = {"running": "⏳", "completed": "✓", "failed": "✗", "pending": "○"}
        icon = icons.get(self._status, "·")
        status_colors = {
            "running": "warning",
            "completed": "green",
            "failed": "red",
            "pending": "dim",
        }
        color = status_colors.get(self._status, "default")

        lines = [f"[{color}]{icon}[/] [tool-name]{self._tool_name}[/]"]
        if self._arguments:
            lines.append(f"    [tool-args]{self._arguments[:100]}[/]")
        if self._status == "completed" and self._output:
            output_preview = self._output[:200]
            lines.append(f"    [dim]→ {output_preview}[/]")
        if self._status == "failed" and self._output:
            lines.append(f"    [red]{self._output[:100]}[/]")
        return "\n".join(lines)

    def update_status(self, status: str, output: str = "") -> None:
        self._status = status
        self._output = output
        self.remove_class("running", "completed", "failed", "pending")
        self.add_class(status)
        self.update(self._render())
