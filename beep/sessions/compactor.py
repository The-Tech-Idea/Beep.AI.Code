"""Session memory compaction — measure, warn, and compact conversation history.

Two compaction strategies are provided:

* ``"trim"``  — local, instant, no LLM call.  Removes oldest message pairs and
  inserts a placeholder tombstone.  Always available.

* ``"summarize"`` — asks the Beep.AI.Server to produce an LLM summary of the
  older turns and collapses them to a single assistant message.  Falls back to
  ``"trim"`` if the server endpoint is unavailable or raises.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal


# ── Thresholds ────────────────────────────────────────────────────────────────

# Soft warning: display inline hint in the REPL status line
WARN_TOKENS: int = 20_000
# Hard auto-compact: compact automatically after each assistant reply
AUTO_COMPACT_TOKENS: int = 60_000
# Absolute ceiling: refuse to grow further; force a compact before next send
HARD_LIMIT_TOKENS: int = 100_000

# Minimum number of exchange *pairs* (user+assistant) to keep after compaction
MIN_TURNS_KEEP: int = 3

CompactionStrategy = Literal["trim", "summarize"]


# ── Stats dataclass ───────────────────────────────────────────────────────────

@dataclass
class SessionMemoryStats:
    """Snapshot of a session's current memory footprint."""

    message_count: int
    token_estimate: int
    char_count: int
    file_size_bytes: int

    @property
    def token_k(self) -> float:
        return self.token_estimate / 1000

    @property
    def usage_pct(self) -> float:
        return min(100.0, (self.token_estimate / AUTO_COMPACT_TOKENS) * 100)

    @property
    def warn_level(self) -> Literal["ok", "warn", "critical"]:
        if self.token_estimate >= HARD_LIMIT_TOKENS:
            return "critical"
        if self.token_estimate >= WARN_TOKENS:
            return "warn"
        return "ok"

    def summary_line(self) -> str:
        lvl_colour = {"ok": "green", "warn": "yellow", "critical": "red"}[self.warn_level]
        bar = _progress_bar(self.usage_pct)
        return (
            f"[{lvl_colour}]{self.token_k:.1f}k tokens[/{lvl_colour}]"
            f" {bar}"
            f" [dim]{self.message_count} msgs · {self.char_count // 1024}KB[/dim]"
        )


def _progress_bar(pct: float, width: int = 10) -> str:
    filled = math.floor(pct / 100 * width)
    return "[dim][[/dim]" + "█" * filled + "░" * (width - filled) + "[dim]][/dim]"


# ── Measurement ───────────────────────────────────────────────────────────────

def measure_session(
    messages: list[dict[str, Any]],
    session_file: "Path | None" = None,  # noqa: F821
) -> SessionMemoryStats:
    """Measure the current memory footprint of *messages*.

    Args:
        messages: The in-memory message list for the session.
        session_file: Optional path to the on-disk JSONL file (for byte size).

    Returns:
        A :class:`SessionMemoryStats` snapshot.
    """
    from pathlib import Path  # local import to keep top-level clean

    total_chars = sum(len(str(m.get("content") or "")) for m in messages)
    token_estimate = total_chars // 4

    file_size = 0
    if session_file is not None and isinstance(session_file, Path) and session_file.exists():
        try:
            file_size = session_file.stat().st_size
        except OSError:
            pass

    return SessionMemoryStats(
        message_count=len(messages),
        token_estimate=token_estimate,
        char_count=total_chars,
        file_size_bytes=file_size,
    )


# ── Compaction result ─────────────────────────────────────────────────────────

@dataclass
class CompactionResult:
    """Outcome of a compaction operation."""

    messages: list[dict[str, Any]]
    stats_before: SessionMemoryStats
    stats_after: SessionMemoryStats
    strategy_used: CompactionStrategy
    server_used: bool

    @property
    def tokens_saved(self) -> int:
        return max(0, self.stats_before.token_estimate - self.stats_after.token_estimate)

    def summary(self) -> str:
        pct = (
            100 * self.tokens_saved // self.stats_before.token_estimate
            if self.stats_before.token_estimate
            else 0
        )
        return (
            f"[green]Compacted[/green] "
            f"{self.stats_before.message_count} → {self.stats_after.message_count} messages "
            f"({self.stats_before.token_estimate // 1000:.1f}k → "
            f"{self.stats_after.token_estimate // 1000:.1f}k tokens, "
            f"-{pct}%)"
        )


# ── Local trim strategy ───────────────────────────────────────────────────────

def _compact_trim(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove oldest message pairs; insert a tombstone placeholder."""
    from beep.agent.context_manager import trim_messages

    return trim_messages(messages, token_budget=AUTO_COMPACT_TOKENS // 2)


# ── LLM summarize strategy ────────────────────────────────────────────────────

async def _compact_summarize(
    messages: list[dict[str, Any]],
    *,
    client: Any,
    session_id: str,
) -> list[dict[str, Any]] | None:
    """Ask the server to summarise older turns into one assistant message.

    Returns ``None`` if the endpoint is unavailable so the caller can fall back.
    """
    try:
        result = await client.compact_conversation(
            session_id=session_id,
            messages=messages,
        )
        compacted = result.get("messages")
        if isinstance(compacted, list) and compacted:
            return compacted
        return None
    except Exception:
        return None


# ── Public compaction entry-point ─────────────────────────────────────────────

async def compact_session(
    messages: list[dict[str, Any]],
    *,
    strategy: CompactionStrategy = "summarize",
    client: Any | None = None,
    session_id: str = "",
    session_file: "Path | None" = None,  # noqa: F821
) -> CompactionResult:
    """Compact *messages* using the requested strategy.

    ``"summarize"`` will attempt a server-side LLM summary and fall back to
    ``"trim"`` if unavailable.  ``"trim"`` always works locally.

    Args:
        messages:     Current in-memory message list.
        strategy:     ``"summarize"`` or ``"trim"``.
        client:       Beep API client (required for ``"summarize"``).
        session_id:   Session ID passed to the server endpoint.
        session_file: Path to the on-disk JSONL for file-size stats.

    Returns:
        A :class:`CompactionResult`.
    """
    stats_before = measure_session(messages, session_file)
    server_used = False
    strategy_used: CompactionStrategy = strategy

    if len(messages) <= 2:
        return CompactionResult(
            messages=messages,
            stats_before=stats_before,
            stats_after=stats_before,
            strategy_used=strategy,
            server_used=False,
        )

    new_messages: list[dict[str, Any]] | None = None

    if strategy == "summarize" and client is not None:
        new_messages = await _compact_summarize(
            messages, client=client, session_id=session_id
        )
        if new_messages is not None:
            server_used = True

    if new_messages is None:
        # Fall back to local trim (also used when strategy=="trim")
        new_messages = _compact_trim(messages)
        strategy_used = "trim"

    stats_after = measure_session(new_messages, session_file)
    return CompactionResult(
        messages=new_messages,
        stats_before=stats_before,
        stats_after=stats_after,
        strategy_used=strategy_used,
        server_used=server_used,
    )
