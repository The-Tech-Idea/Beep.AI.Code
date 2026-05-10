"""Multi-line input handling for REPL with tab completion.

Uses prompt_toolkit for:
- Tab completion (commands, file paths)
- Command history
- Multi-line input
"""

from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, merge_completers
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import CompleteStyle

from beep.workspace.detector import find_workspace_root
from beep.workspace.ignore import IgnoreMatcher

HISTORY_FILE = Path.home() / ".beepai" / "chat_history"


class PathCompleter(Completer):
    """Complete file paths after @ mentions."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._root = workspace_root or find_workspace_root()
        self._matcher = IgnoreMatcher(self._root)

    def get_completions(self, document: Document, _) -> list[Completion]:
        text = document.text_before_cursor

        if "@" not in text:
            return

        at_idx = text.rfind("@")
        partial = text[at_idx + 1:]

        search_dir = self._root
        if "/" in partial:
            dir_part = partial.rsplit("/", 1)[0]
            search_dir = self._root / dir_part
            prefix = dir_part + "/"
        else:
            prefix = ""

        if not search_dir.exists():
            return

        partial_lower = partial.rsplit("/", 1)[-1].lower()

        try:
            for entry in search_dir.iterdir():
                if self._matcher.is_ignored(entry):
                    continue
                if entry.name.lower().startswith(partial_lower):
                    if entry.is_dir():
                        yield Completion(
                            prefix + entry.name + "/",
                            start_position=-len(partial),
                            display=entry.name + "/",
                            display_meta="dir",
                        )
                    else:
                        yield Completion(
                            prefix + entry.name,
                            start_position=-len(partial),
                            display=entry.name,
                            display_meta="file",
                        )
        except PermissionError:
            pass


class SlashCompleter(Completer):
    """Complete slash commands."""

    def __init__(self, commands: dict[str, str] | None = None) -> None:
        self._commands = commands or {}

    def get_completions(self, document: Document, _) -> list[Completion]:
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        word = document.get_word_before_cursor()
        for name, desc in self._commands.items():
            if name.startswith(word.lstrip("/")):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display=f"/{name}",
                    display_meta=desc,
                )


def create_completer(
    commands: dict[str, str] | None = None,
    workspace_root: Path | None = None,
) -> Completer:
    """Create merged completer for commands and paths."""
    return merge_completers([
        SlashCompleter(commands),
        PathCompleter(workspace_root),
    ])


def read_multiline(
    prompt_text: str = "> ",
    commands: dict[str, str] | None = None,
    workspace_root: Path | None = None,
) -> str | None:
    """Read input with tab completion and history.

    Tab completes:
    - /commands when text starts with /
    - @file paths when text contains @

    Returns None on EOF/Ctrl+D.
    """
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    kb = KeyBindings()

    @kb.add("c-d")
    def _eof(event) -> None:
        if not event.current_buffer.text:
            event.app.exit(result=None)

    session = PromptSession(
        message=prompt_text,
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=create_completer(commands, workspace_root),
        complete_style=CompleteStyle.MULTI_COLUMN,
        complete_while_typing=True,
        key_bindings=kb,
        enable_history_search=True,
    )

    try:
        result = session.prompt()
    except (KeyboardInterrupt, EOFError):
        return None

    return result.strip() or None
