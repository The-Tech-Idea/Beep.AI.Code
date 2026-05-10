"""Presentation helpers for session summaries."""

from __future__ import annotations

from rich.table import Table

from beep.sessions.history import SessionSummary, _relative_time


def build_sessions_table(
    summaries: list[SessionSummary],
    *,
    title: str,
    limit: int = 20,
    preview_width: int = 60,
    preview_column_width: int = 40,
) -> Table:
    """Build a shared table view for session summaries."""
    table = Table(title=title)
    table.add_column("ID", style="cyan")
    table.add_column("Messages", justify="right")
    table.add_column("Created", style="dim")
    table.add_column("Preview", style="dim", no_wrap=False, max_width=preview_column_width)

    for summary in summaries[:limit]:
        table.add_row(
            summary.session_id,
            str(summary.message_count),
            _relative_time(summary.created_at),
            summary.last_message_preview[:preview_width] if summary.last_message_preview else "",
        )

    return table