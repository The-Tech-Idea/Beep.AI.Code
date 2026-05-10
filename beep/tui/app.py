"""Main TUI application — OpenCode-style terminal workbench."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header

from beep import __version__
from beep.chat.repl import ChatSession
from beep.config import BeepConfig
from beep.tui.dialogs.command_palette import CommandEntry, CommandPalette
from beep.tui.dialogs.file_picker import FilePicker
from beep.tui.dialogs.help import HelpDialog
from beep.tui.dialogs.model_selector import ModelSelector
from beep.tui.dialogs.session_switcher import SessionSwitcher
from beep.tui.screens.chat import ChatScreen


class TUIApp(App):
    """Main Beep.AI.Code TUI — keyboard-driven terminal workbench."""

    TITLE = f"Beep.AI.Code v{__version__}"
    SUB_TITLE = "Terminal Workbench"

    CSS = """
    Screen {
        background: $background;
    }
    Header {
        dock: top;
    }
    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        ("ctrl+p", "command_palette", "Commands"),
        ("ctrl+s", "session_switcher", "Sessions"),
        ("ctrl+o", "model_selector", "Models"),
        ("ctrl+f", "file_picker", "Files"),
        ("ctrl+n", "new_session", "New session"),
        ("ctrl+k", "compact_session", "Compact"),
        ("ctrl+?", "help", "Help"),
        ("ctrl+c", "quit", "Quit"),
    ]

    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250414",
        "claude-haiku-3-5-20241022",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "llama-3-70b",
        "qwen-2.5-coder-32b",
    ]

    def __init__(
        self,
        config: BeepConfig,
        *,
        model: str | None = None,
        mode: str = "assistant",
    ) -> None:
        super().__init__()
        self._config = config
        self._model = model or config.default_model or "default"
        self._mode = mode
        self._client: BeepAPIClient | None = None
        self._chat_session: ChatSession | None = None
        self._workspace_root = Path.cwd()
        self._messages: list[dict[str, str]] = []
        self._tool_calls_visible = True

    def on_mount(self) -> None:
        from beep.app_service import get_app_service

        self._client = get_app_service().api_client(self._config)
        self.sub_title = f"Model: {self._model} | {self._mode}"
        self.push_screen(ChatScreen(workspace_root=self._workspace_root))

    def _get_commands(self) -> list[CommandEntry]:
        return [
            CommandEntry(
                "New Session", "Start a fresh conversation", "Ctrl+N", self._cmd_new_session
            ),
            CommandEntry(
                "Switch Session", "Browse and switch sessions", "Ctrl+S", self._cmd_sessions
            ),
            CommandEntry("Select Model", "Change the LLM model", "Ctrl+O", self._cmd_models),
            CommandEntry(
                "Compact Session", "Summarize long conversation", "Ctrl+K", self._cmd_compact
            ),
            CommandEntry("Toggle Mode", "Switch Plan/Build mode", "Tab", None),
            CommandEntry("File Picker", "Attach files to message", "Ctrl+F", None),
            CommandEntry(
                "Toggle Tool Calls", "Show/hide tool executions", "", self._cmd_toggle_tools
            ),
            CommandEntry("Help", "Show keyboard shortcuts", "Ctrl+?", None),
            CommandEntry("Quit", "Exit TUI", "Ctrl+C", lambda: self.exit()),
        ]

    def action_command_palette(self) -> None:
        def on_select(cmd: CommandEntry | None) -> None:
            if cmd and cmd.callback:
                cmd.callback()

        self.push_screen(CommandPalette(self._get_commands()), on_select)

    def action_session_switcher(self) -> None:
        sessions = self._list_sessions()
        current = ""

        def on_select(session_id: str | None) -> None:
            if session_id == "__new__":
                self._cmd_new_session()
            elif session_id:
                self._resume_session(session_id)

        self.push_screen(SessionSwitcher(sessions, current), on_select)

    def action_model_selector(self) -> None:
        def on_select(model: str | None) -> None:
            if model:
                self._model = model
                self.sub_title = f"Model: {self._model} | {self._mode}"
                chat = self.query_one(ChatScreen)
                if chat:
                    chat.update_status(model=model)

        self.push_screen(ModelSelector(self.AVAILABLE_MODELS, self._model), on_select)

    def action_file_picker(self) -> None:
        def on_select(files: list[str] | None) -> None:
            if files:
                chat = self.query_one(ChatScreen)
                if chat:
                    chat._attached_files = files

        self.push_screen(FilePicker(self._workspace_root), on_select)

    def action_new_session(self) -> None:
        self._cmd_new_session()

    def action_compact_session(self) -> None:
        self._cmd_compact()

    def action_help(self) -> None:
        self.push_screen(HelpDialog())

    def _cmd_new_session(self) -> None:
        self._messages = []
        chat = self.query_one(ChatScreen)
        if chat:
            chat._messages = []
            chat._tool_calls = []
            log = chat.query_one("#chat-log")
            if log:
                log.clear()
            tool_container = chat.query_one("#tool-calls")
            if tool_container:
                for child in tool_container.children:
                    child.remove()
        self.notify("New session started")

    def _cmd_compact(self) -> None:
        self.notify("Session compacted")

    def _cmd_sessions(self) -> None:
        self.action_session_switcher()

    def _cmd_models(self) -> None:
        self.action_model_selector()

    def _cmd_toggle_tools(self) -> None:
        self._tool_calls_visible = not self._tool_calls_visible
        container = self.query_one("#tool-calls")
        if container:
            container.display = self._tool_calls_visible
        self.notify(f"Tool calls {'shown' if self._tool_calls_visible else 'hidden'}")

    def _list_sessions(self) -> list[dict]:
        try:
            from beep.sessions.history import list_sessions as _list

            sessions = _list()
            return [
                {
                    "id": s.session_id,
                    "title": getattr(s, "title", "Untitled"),
                    "message_count": getattr(s, "message_count", 0),
                    "updated_at": getattr(s, "updated_at", ""),
                }
                for s in sessions
            ]
        except Exception:
            return []

    def _resume_session(self, session_id: str) -> None:
        self._messages = []
        try:
            from beep.sessions.history import load_session

            messages = load_session(session_id)
            self._messages = messages
        except Exception:
            pass
        self._cmd_new_session()
        self.notify(f"Switched to session {session_id[:8]}")


def run_tui(
    config: BeepConfig,
    *,
    model: str | None = None,
    mode: str = "assistant",
) -> None:
    """Run the TUI application."""
    app = TUIApp(config, model=model, mode=mode)
    app.run()
