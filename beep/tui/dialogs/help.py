"""Help dialog (Ctrl+?)."""

from __future__ import annotations

from textual.screen import ModalScreen
from textual.widgets import Static


class HelpDialog(ModalScreen):
    """Help dialog showing all available keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpDialog {
        align: center middle;
    }
    HelpDialog > .help-container {
        width: 60;
        height: 25;
        background: $surface;
        border: tall $primary;
        padding: 1;
        overflow: auto;
    }
    HelpDialog #help-title {
        text-style: bold;
        color: $primary;
        padding: 0 0 1 0;
    }
    HelpDialog .section-header {
        text-style: bold underline;
        padding: 1 0 0 0;
    }
    HelpDialog .shortcut {
        padding: 0 0 0 2;
    }
    HelpDialog .key {
        color: $primary;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def compose(self):
        content = (
            "[#help-title][bold]Keyboard Shortcuts[/][/]\n"
            "\n"
            "[.section-header]Navigation[/]\n"
            "  [.key]Ctrl+P[/]    Command palette\n"
            "  [.key]Ctrl+S[/]    Session switcher\n"
            "  [.key]Ctrl+O[/]    Model selector\n"
            "  [.key]Ctrl+F[/]    File picker\n"
            "  [.key]Ctrl+N[/]    New session\n"
            "  [.key]Ctrl+L[/]    View logs\n"
            "\n"
            "[.section-header]Chat[/]\n"
            "  [.key]Enter[/]     Send message\n"
            "  [.key]Shift+Enter[/] New line\n"
            "  [.key]Ctrl+E[/]    Open external editor\n"
            "  [.key]Ctrl+U/D[/]  Scroll up/down\n"
            "  [.key]Ctrl+C[/]    Cancel / Quit\n"
            "\n"
            "[.section-header]Modes[/]\n"
            "  [.key]Tab[/]       Toggle Plan/Build mode\n"
            "  [.key]Ctrl+K[/]    Compact session\n"
            "\n"
            "[.section-header]Session[/]\n"
            "  [.key]/undo[/]     Undo last message\n"
            "  [.key]/redo[/]     Redo last message\n"
            "  [.key]/clear[/]    Clear chat history\n"
            "  [.key]/sessions[/] List all sessions\n"
            "\n"
            "[.section-header]Other[/]\n"
            "  [.key]@file[/]     Reference a file\n"
            "  [.key]!cmd[/]      Run shell command\n"
            "  [.key]/help[/]     Show this help\n"
            "\n"
            "[dim]Press Esc to close[/]"
        )
        yield Static(content)

    def action_close(self) -> None:
        self.dismiss()
