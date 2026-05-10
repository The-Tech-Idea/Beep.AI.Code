"""Permission dialog for tool actions."""

from __future__ import annotations

from dataclasses import dataclass

from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


@dataclass
class PermissionRequest:
    """A permission request for a tool action."""

    tool_name: str
    description: str
    details: str = ""
    action: str = "execute"


class PermissionDialog(ModalScreen):
    """Dialog requesting permission for a tool action."""

    DEFAULT_CSS = """
    PermissionDialog {
        align: center middle;
    }
    PermissionDialog > .dialog-container {
        width: 60;
        height: auto;
        background: $surface;
        border: tall $warning;
        padding: 1;
    }
    PermissionDialog #permission-title {
        text-style: bold;
        color: $warning;
        padding: 0 0 1 0;
    }
    PermissionDialog #permission-details {
        padding: 1 0;
    }
    PermissionDialog .button-row {
        align: center middle;
        height: 3;
    }
    PermissionDialog Button {
        margin: 0 1;
    }
    PermissionDialog #btn-allow {
        background: $success;
    }
    PermissionDialog #btn-deny {
        background: $error;
    }
    PermissionDialog #btn-always {
        background: $primary;
    }
    """

    BINDINGS = [
        ("a", "allow", "Allow"),
        ("d", "deny", "Deny"),
        ("escape", "deny", "Deny"),
    ]

    def __init__(self, request: PermissionRequest, **kwargs) -> None:
        super().__init__(**kwargs)
        self._request = request

    def compose(self):
        yield Static("[bold]⚠ Permission Required[/]", id="permission-title")
        yield Static(
            f"[bold]{self._request.tool_name}[/]\n\n"
            f"{self._request.description}\n\n"
            f"[dim]{self._request.details}[/]",
            id="permission-details",
        )
        yield Static(
            "[dim][A]llow  [D]eny[/]",
            classes="button-row",
        )

    def action_allow(self) -> None:
        self.dismiss("allow")

    def action_deny(self) -> None:
        self.dismiss("deny")
