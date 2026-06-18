"""Edit checkpoint timeline commands — /undo restore + /checkpoints list."""

from __future__ import annotations

from typing import Any

from beep.chat.commands.base import Command
from beep.utils.console import get_console


def _get_timeline(session: Any) -> Any:
    tl = getattr(session, "_checkpoint_timeline", None)
    if tl is None:
        from beep.chat.checkpoint_timeline import CheckpointTimeline

        tl = CheckpointTimeline()
        session._checkpoint_timeline = tl
    return tl


class UndoEditCommand(Command):
    @property
    def name(self) -> str:
        return "undoedit"

    @property
    def description(self) -> str:
        return "Undo the last file edit (restore from checkpoint)"

    @property
    def category(self) -> str:
        return "Chat"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        timeline = _get_timeline(session)
        if len(timeline) == 0:
            get_console().print("[yellow]No file edits to undo.[/yellow]")
            return
        cp = timeline.restore_last()
        if cp is None:
            get_console().print("[yellow]Nothing to restore.[/yellow]")
        else:
            get_console().print(
                f"[green]Restored '{cp.file_path.name}' to state before '{cp.tool_name}'.[/green]"
            )


class CheckpointsCommand(Command):
    @property
    def name(self) -> str:
        return "checkpoints"

    @property
    def description(self) -> str:
        return "List file edit checkpoints (undo timeline)"

    @property
    def category(self) -> str:
        return "Chat"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        session = ctx["session"]
        timeline = _get_timeline(session)
        points = timeline.list_checkpoints()
        if not points:
            get_console().print("[dim]No edit checkpoints yet.[/dim]")
            return
        get_console().print(f"[bold]Edit checkpoints ({len(points)}):[/bold]")
        for p in points:
            get_console().print(
                f"  [{p['index']}] {p['tool']} → {p['file']} [dim]({p['timestamp'][:19]})[/dim]"
            )
