"""Session commands: /clear, /resume, /sessions, /session, /compact, /memory."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command
from beep.chat.session_runtime_state import clear_session_runtime_state
from beep.sessions.history import (
    create_session_id,
    export_session,
    list_sessions,
    replace_session,
)
from beep.sessions.presentation import build_sessions_table
from beep.sessions.compactor import (
    compact_session,
    measure_session,
    AUTO_COMPACT_TOKENS,
    WARN_TOKENS,
    HARD_LIMIT_TOKENS,
)



from beep.utils.console import get_console
class ClearCommand(Command):
    @property
    def name(self) -> str:
        return "clear"

    @property
    def description(self) -> str:
        return "Start new session"

    @property
    def category(self) -> str:
        return "Chat"

    @property
    def aliases(self) -> list[str]:
        return ["c"]

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        session._session_id = create_session_id()
        session.clear_history()
        session._token_count = 0
        session._request_count = 0
        session._last_output = ""
        session._coding_project_id = None
        session._coding_session_id = None
        clear_session_runtime_state(session)
        get_console().print(f"[green]New session: {session._session_id}[/green]")


class CompactCommand(Command):
    @property
    def name(self) -> str:
        return "compact"

    @property
    def description(self) -> str:
        return "Compress conversation history (compact [summarize|trim])"

    @property
    def category(self) -> str:
        return "Chat"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        if len(session._messages) <= 2:
            get_console().print("[yellow]Nothing to compact[/yellow]")
            return

        arg = args.strip().lower()
        strategy = "trim" if arg == "trim" else "summarize"

        from beep.sessions.history import HISTORY_DIR
        session_file = HISTORY_DIR / f"{session._session_id}.jsonl"

        result = await compact_session(
            session._messages,
            strategy=strategy,
            client=ctx.get("client"),
            session_id=session._session_id,
            session_file=session_file,
        )

        session._messages = result.messages
        replace_session(session._session_id, session._messages)

        # Reset memory watcher so the next send doesn't re-fire immediately
        watcher = getattr(session, "_memory_watcher", None)
        if watcher is not None:
            watcher.reset()

        via = "server" if result.server_used else "local"
        get_console().print(
            f"{result.summary()} [dim]({via} {result.strategy_used})[/dim]"
        )


class MemoryCommand(Command):
    """Show current session memory consumption and compaction settings."""

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Show session memory usage and compaction settings"

    @property
    def category(self) -> str:
        return "Chat"

    @property
    def aliases(self) -> list[str]:
        return ["mem"]

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        console = get_console()

        arg = args.strip().lower()

        if arg in ("auto on", "auto-on", "auto_on"):
            session._auto_compact = True
            console.print("[green]Auto-compact enabled[/green]")
            return

        if arg in ("auto off", "auto-off", "auto_off"):
            session._auto_compact = False
            console.print("[yellow]Auto-compact disabled[/yellow]")
            return

        from beep.sessions.history import HISTORY_DIR
        session_file = HISTORY_DIR / f"{session._session_id}.jsonl"
        stats = measure_session(session._messages, session_file)

        auto_compact = getattr(session, "_auto_compact", True)
        auto_label = "[green]on[/green]" if auto_compact else "[yellow]off[/yellow]"

        console.print(f"\n[bold]Session memory[/bold] — {session._session_id[:16]}…")
        console.print(f"  Messages   : {stats.message_count}")
        console.print(f"  ~Tokens    : {stats.token_estimate:,} ({stats.token_k:.1f}k)")
        console.print(f"  Chars      : {stats.char_count:,}")
        if stats.file_size_bytes:
            console.print(f"  Disk       : {stats.file_size_bytes / 1024:.1f} KB")
        console.print(f"  Usage      : {stats.summary_line()}")
        console.print()
        console.print(f"  Warn at         ~{WARN_TOKENS // 1000}k tokens")
        console.print(f"  Auto-compact at ~{AUTO_COMPACT_TOKENS // 1000}k tokens")
        console.print(f"  Hard limit at   ~{HARD_LIMIT_TOKENS // 1000}k tokens")
        console.print(f"  Auto-compact    : {auto_label}")
        console.print()
        console.print(
            "  [dim]/compact          — compact now (tries server summarize, falls back to trim)[/dim]"
        )
        console.print("  [dim]/compact trim     — local trim only[/dim]")
        console.print("  [dim]/memory auto on   — enable auto-compact[/dim]")
        console.print("  [dim]/memory auto off  — disable auto-compact[/dim]")
        console.print()


class UndoCommand(Command):
    @property
    def name(self) -> str:
        return "undo"

    @property
    def description(self) -> str:
        return "Remove last user/assistant exchange"

    @property
    def category(self) -> str:
        return "Chat"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        msgs = session._messages
        # Need at least system + user to have something to undo
        if len(msgs) < 2:
            get_console().print("[yellow]Nothing to undo[/yellow]")
            return
        # Remove the last assistant then the last user message
        if msgs[-1].get("role") == "assistant" and msgs[-2].get("role") == "user":
            session._messages = msgs[:-2]
            get_console().print("[green]Last exchange removed[/green]")
        elif msgs[-1].get("role") == "user":
            session._messages = msgs[:-1]
            get_console().print("[green]Last message removed[/green]")
        else:
            get_console().print("[yellow]Nothing to undo[/yellow]")


class ResumeCommand(Command):
    @property
    def name(self) -> str:
        return "resume"

    @property
    def description(self) -> str:
        return "Resume a previous session"

    @property
    def category(self) -> str:
        return "Chat"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /resume <session_id>[/yellow]")
            return
        session = ctx["session"]
        session.resume_session(args)


class SessionCommand(Command):
    @property
    def name(self) -> str:
        return "session"

    @property
    def description(self) -> str:
        return "Show current session ID"

    @property
    def category(self) -> str:
        return "Chat"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        get_console().print(f"Session: [cyan]{session._session_id}[/cyan]")


class SessionsCommand(Command):
    @property
    def name(self) -> str:
        return "sessions"

    @property
    def description(self) -> str:
        return "List, export, or search sessions"

    @property
    def category(self) -> str:
        return "Chat"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        parts = args.strip().split(None, 1)
        sub = parts[0].lower() if parts else "list"
        sub_args = parts[1] if len(parts) > 1 else ""

        if sub in ("list", ""):
            await self._list()
        elif sub == "export":
            await self._export(sub_args.strip())
        else:
            # Treat bare /sessions as /sessions list
            await self._list()

    async def _list(self) -> None:
        summaries = list_sessions()
        if not summaries:
            get_console().print("[yellow]No sessions[/yellow]")
            return

        get_console().print(build_sessions_table(summaries, title="Sessions"))

    async def _export(self, args: str) -> None:
        parts = args.split(None, 1)
        if not parts:
            get_console().print("[yellow]Usage: /sessions export <session_id> [md|json][/yellow]")
            return
        sid = parts[0]
        fmt = parts[1].strip() if len(parts) > 1 else "md"
        if fmt not in ("md", "json"):
            get_console().print("[yellow]Format must be 'md' or 'json'[/yellow]")
            return
        output = export_session(sid, format=fmt)
        if not output:
            get_console().print(f"[yellow]No session found: {sid}[/yellow]")
            return
        get_console().print(output)


DEFAULT_SESSION_COMMANDS = [
    ClearCommand,
    CompactCommand,
    MemoryCommand,
    UndoCommand,
    ResumeCommand,
    SessionCommand,
    SessionsCommand,
]
