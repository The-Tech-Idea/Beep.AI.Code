"""Per-session memory watcher.

Watches the in-memory message list of a chat session and emits
:class:`MemoryWarning` objects when thresholds are crossed.

Usage::

    watcher = MemoryWatcher()
    warning = watcher.check(session._messages)
    if warning:
        console.print(warning.render())
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from beep.sessions.compactor import (
    AUTO_COMPACT_TOKENS,
    HARD_LIMIT_TOKENS,
    WARN_TOKENS,
    SessionMemoryStats,
    measure_session,
)


# ── Warning dataclass ─────────────────────────────────────────────────────────

@dataclass
class MemoryWarning:
    """A warning emitted when a session's memory usage crosses a threshold."""

    level: Literal["warn", "critical"]
    stats: SessionMemoryStats
    suggestion: str

    def render(self) -> str:
        """Return a Rich-markup string suitable for printing to the console."""
        icon = "⚠" if self.level == "warn" else "🔴"
        colour = "yellow" if self.level == "warn" else "red"
        return (
            f"[{colour}]{icon} Session memory: {self.stats.summary_line()}[/{colour}]"
            f" [dim]— {self.suggestion}[/dim]"
        )


# ── Memory watcher ────────────────────────────────────────────────────────────

class MemoryWatcher:
    """Stateful watcher for a single chat session's message list.

    Deduplicates repeated warnings at the same threshold so users are not
    spammed.  A warning is re-emitted only after the usage level changes or
    drops back below the threshold.
    """

    def __init__(
        self,
        *,
        warn_tokens: int = WARN_TOKENS,
        auto_compact_tokens: int = AUTO_COMPACT_TOKENS,
        hard_limit_tokens: int = HARD_LIMIT_TOKENS,
    ) -> None:
        self._warn_tokens = warn_tokens
        self._auto_compact_tokens = auto_compact_tokens
        self._hard_limit_tokens = hard_limit_tokens
        self._last_warn_level: str = "ok"

    @property
    def warn_tokens(self) -> int:
        return self._warn_tokens

    @property
    def auto_compact_tokens(self) -> int:
        return self._auto_compact_tokens

    @property
    def hard_limit_tokens(self) -> int:
        return self._hard_limit_tokens

    def check(
        self,
        messages: list[dict[str, Any]],
        session_file: "Path | None" = None,  # noqa: F821
    ) -> MemoryWarning | None:
        """Check *messages* and return a :class:`MemoryWarning` if a threshold
        is crossed, or ``None`` when usage is healthy.

        Consecutive calls at the same level are suppressed to avoid noise.
        """
        stats = measure_session(messages, session_file)
        level = _classify(
            stats.token_estimate,
            warn=self._warn_tokens,
            critical=self._auto_compact_tokens,
        )

        if level == "ok":
            self._last_warn_level = "ok"
            return None

        if level == self._last_warn_level:
            # Same level as before — suppress repeat
            return None

        self._last_warn_level = level
        suggestion = _make_suggestion(level, stats)
        return MemoryWarning(level=level, stats=stats, suggestion=suggestion)

    def should_auto_compact(self, messages: list[dict[str, Any]]) -> bool:
        """Return ``True`` when the session has grown past the auto-compact
        threshold and compaction should be triggered before the next send."""
        stats = measure_session(messages)
        return stats.token_estimate >= self._auto_compact_tokens

    def should_block(self, messages: list[dict[str, Any]]) -> bool:
        """Return ``True`` when the session is at the hard limit and no further
        messages should be appended without compaction first."""
        stats = measure_session(messages)
        return stats.token_estimate >= self._hard_limit_tokens

    def reset(self) -> None:
        """Reset warning state (e.g. after a successful compaction)."""
        self._last_warn_level = "ok"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify(
    tokens: int,
    *,
    warn: int,
    critical: int,
) -> Literal["ok", "warn", "critical"]:
    if tokens >= critical:
        return "critical"
    if tokens >= warn:
        return "warn"
    return "ok"


def _make_suggestion(
    level: Literal["warn", "critical"],
    stats: SessionMemoryStats,
) -> str:
    if level == "critical":
        return (
            "Session is large. Run [bold]/compact[/bold] to summarise history "
            "or [bold]/clear[/bold] to start fresh."
        )
    return (
        f"~{stats.token_k:.1f}k tokens used. "
        "Type [bold]/memory[/bold] for details."
    )
