"""Main chat screen with streaming and tool calls."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, RichLog, Static

from beep.tui.widgets.message_display import MessageDisplay
from beep.tui.widgets.sidebar import SessionSidebar
from beep.tui.widgets.status_bar import StatusBar
from beep.tui.widgets.tool_call import ToolCallDisplay


class ChatScreen(Container):
    """Main chat screen with sidebar and status bar."""

    DEFAULT_CSS = """
    ChatScreen {
        layout: vertical;
    }
    #main-area {
        height: 1fr;
        layout: horizontal;
    }
    #chat-area {
        width: 1fr;
        padding: 0 1;
    }
    #chat-log {
        height: 1fr;
        overflow: auto;
    }
    #input-area {
        height: auto;
        dock: bottom;
        padding: 1 0 0 0;
    }
    #input-area Input {
        width: 100%;
    }
    #tool-calls {
        height: auto;
        max-height: 8;
        overflow: auto;
    }
    #mode-indicator {
        dock: bottom;
        height: 1;
        text-align: center;
    }
    #mode-indicator.plan {
        color: $warning;
        text-style: bold;
    }
    #mode-indicator.build {
        color: $success;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("tab", "toggle_mode", "Toggle mode"),
        ("ctrl+p", "command_palette", "Commands"),
        ("ctrl+s", "session_switcher", "Sessions"),
        ("ctrl+o", "model_selector", "Models"),
        ("ctrl+f", "file_picker", "Files"),
        ("ctrl+n", "new_session", "New session"),
        ("ctrl+?", "help", "Help"),
    ]

    def __init__(
        self,
        workspace_root: Path | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._workspace_root = workspace_root or Path.cwd()
        self._mode = "build"
        self._messages: list[dict[str, str]] = []
        self._tool_calls: list[dict] = []
        self._attached_files: list[str] = []

    def compose(self):
        yield Static(id="mode-indicator")
        yield Horizontal(
            Vertical(
                RichLog(id="chat-log", markup=True, wrap=True, highlight=True),
                Vertical(id="tool-calls"),
                Input(
                    id="chat-input",
                    placeholder="Message... (Ctrl+P for commands, Tab to toggle mode)",
                ),
                id="chat-area",
            ),
            SessionSidebar(id="sidebar"),
            id="main-area",
        )
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        self._update_mode_indicator()
        self.query_one("#chat-input", Input).focus()

    def _update_mode_indicator(self) -> None:
        indicator = self.query_one("#mode-indicator", Static)
        indicator.remove_class("plan", "build")
        indicator.add_class(self._mode)
        if self._mode == "plan":
            indicator.update("📋 PLAN MODE — Analysis only, no file changes")
        else:
            indicator.update("🔨 BUILD MODE — Full tool access")

    def action_toggle_mode(self) -> None:
        self._mode = "plan" if self._mode == "build" else "build"
        self._update_mode_indicator()
        sidebar = self.query_one("#sidebar", SessionSidebar)
        if sidebar:
            sidebar.set_title(f"Session ({self._mode})")

    def action_command_palette(self) -> None:
        pass

    def action_session_switcher(self) -> None:
        pass

    def action_model_selector(self) -> None:
        pass

    def action_file_picker(self) -> None:
        pass

    def action_new_session(self) -> None:
        pass

    def action_help(self) -> None:
        pass

    def add_message(self, role: str, content: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        msg = MessageDisplay(role=role, content=content)
        log.write(msg.renderable if hasattr(msg, "renderable") else msg._render_message())
        self._messages.append({"role": role, "content": content})

    def add_tool_call(self, name: str, args: str = "", status: str = "running") -> None:
        container = self.query_one("#tool-calls", Vertical)
        display = ToolCallDisplay(tool_name=name, arguments=args, status=status)
        container.mount(display)
        self._tool_calls.append({"name": name, "args": args, "status": status})

        sidebar = self.query_one("#sidebar", SessionSidebar)
        if sidebar:
            sidebar.add_tool_call(name, status)

    def add_modified_file(self, path: str) -> None:
        sidebar = self.query_one("#sidebar", SessionSidebar)
        if sidebar:
            sidebar.add_modified_file(path)

    def update_status(self, **kwargs) -> None:
        bar = self.query_one("#status-bar", StatusBar)
        if bar:
            if "model" in kwargs:
                bar.set_model(kwargs["model"])
            if "session" in kwargs:
                bar.set_session(kwargs["session"])
            if "mode" in kwargs:
                bar.set_mode(kwargs["mode"])
            if "tokens" in kwargs:
                count = kwargs["tokens"]
                budget = kwargs.get("token_budget", 0)
                bar.set_tokens(count, budget)
