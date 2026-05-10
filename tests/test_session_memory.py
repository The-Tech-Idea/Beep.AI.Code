"""Tests for beep/sessions/compactor.py and beep/sessions/memory_watch.py."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from beep.sessions.compactor import (
    AUTO_COMPACT_TOKENS,
    HARD_LIMIT_TOKENS,
    WARN_TOKENS,
    CompactionResult,
    SessionMemoryStats,
    compact_session,
    measure_session,
)
from beep.sessions.memory_watch import MemoryWarning, MemoryWatcher


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_messages(n_pairs: int, chars_each: int = 100) -> list[dict]:
    """Return [system, user, assistant, user, assistant, ...] with n_pairs turns."""
    msgs = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(n_pairs):
        msgs.append({"role": "user", "content": "x" * chars_each})
        msgs.append({"role": "assistant", "content": "y" * chars_each})
    return msgs


def _big_messages(token_target: int) -> list[dict]:
    """Return a messages list whose estimated token count exceeds token_target.

    Uses multiple pairs so trim_messages has at least one pair to remove.
    """
    # Spread across 6 pairs so the trimmer has something to cut
    chars_per_msg = max(100, token_target * 4 // 12 + 1)
    return _make_messages(6, chars_each=chars_per_msg)


# ── SessionMemoryStats ────────────────────────────────────────────────────────

class TestSessionMemoryStats:
    def test_token_k(self):
        stats = SessionMemoryStats(
            message_count=5,
            token_estimate=12_000,
            char_count=48_000,
            file_size_bytes=0,
        )
        assert stats.token_k == pytest.approx(12.0)

    def test_usage_pct_capped_at_100(self):
        stats = SessionMemoryStats(
            message_count=1,
            token_estimate=AUTO_COMPACT_TOKENS * 2,
            char_count=0,
            file_size_bytes=0,
        )
        assert stats.usage_pct == 100.0

    def test_warn_level_ok(self):
        stats = SessionMemoryStats(0, WARN_TOKENS - 1, 0, 0)
        assert stats.warn_level == "ok"

    def test_warn_level_warn(self):
        stats = SessionMemoryStats(0, WARN_TOKENS, 0, 0)
        assert stats.warn_level == "warn"

    def test_warn_level_critical(self):
        stats = SessionMemoryStats(0, HARD_LIMIT_TOKENS, 0, 0)
        assert stats.warn_level == "critical"

    def test_summary_line_contains_tokens(self):
        stats = SessionMemoryStats(3, 5_000, 20_000, 0)
        line = stats.summary_line()
        assert "5.0k tokens" in line


# ── measure_session ───────────────────────────────────────────────────────────

class TestMeasureSession:
    def test_empty_returns_zero(self):
        stats = measure_session([])
        assert stats.message_count == 0
        assert stats.token_estimate == 0

    def test_counts_messages(self):
        msgs = _make_messages(3)  # system + 6 = 7 total
        stats = measure_session(msgs)
        assert stats.message_count == 7

    def test_token_estimate_from_chars(self):
        # 400 chars ≈ 100 tokens
        msgs = [{"role": "user", "content": "a" * 400}]
        stats = measure_session(msgs)
        assert stats.token_estimate == 100

    def test_char_count_sum(self):
        msgs = [
            {"role": "user", "content": "a" * 200},
            {"role": "assistant", "content": "b" * 300},
        ]
        stats = measure_session(msgs)
        assert stats.char_count == 500

    def test_file_size_zero_if_no_file(self):
        stats = measure_session([{"role": "user", "content": "hi"}])
        assert stats.file_size_bytes == 0

    def test_file_size_from_real_file(self, tmp_path):
        p = tmp_path / "session.jsonl"
        p.write_text("dummy content", encoding="utf-8")
        stats = measure_session([{"role": "user", "content": "hi"}], session_file=p)
        assert stats.file_size_bytes == p.stat().st_size


# ── compact_session — trim strategy ──────────────────────────────────────────

class TestCompactSessionTrim:
    @pytest.mark.asyncio
    async def test_no_op_when_only_system(self):
        msgs = [{"role": "system", "content": "sys"}]
        result = await compact_session(msgs, strategy="trim")
        assert result.messages is msgs  # unchanged

    @pytest.mark.asyncio
    async def test_no_op_with_only_two_messages(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        result = await compact_session(msgs, strategy="trim")
        assert result.messages is msgs

    @pytest.mark.asyncio
    async def test_trim_reduces_large_session(self):
        msgs = _big_messages(AUTO_COMPACT_TOKENS + 10_000)
        result = await compact_session(msgs, strategy="trim")
        assert result.stats_after.token_estimate < result.stats_before.token_estimate

    @pytest.mark.asyncio
    async def test_result_preserves_system_message(self):
        msgs = _make_messages(10, chars_each=2000)
        result = await compact_session(msgs, strategy="trim")
        assert result.messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_strategy_used_is_trim(self):
        msgs = _make_messages(10, chars_each=2000)
        result = await compact_session(msgs, strategy="trim")
        assert result.strategy_used == "trim"
        assert result.server_used is False

    @pytest.mark.asyncio
    async def test_summary_shows_reduction(self):
        msgs = _make_messages(10, chars_each=2000)
        result = await compact_session(msgs, strategy="trim")
        summary = result.summary()
        assert "→" in summary

    @pytest.mark.asyncio
    async def test_tokens_saved_non_negative(self):
        msgs = _make_messages(10, chars_each=2000)
        result = await compact_session(msgs, strategy="trim")
        assert result.tokens_saved >= 0


# ── compact_session — summarize strategy ─────────────────────────────────────

class TestCompactSessionSummarize:
    @pytest.mark.asyncio
    async def test_uses_server_when_available(self):
        server_msgs = [
            {"role": "system", "content": "sys"},
            {"role": "assistant", "content": "summary"},
        ]
        client = MagicMock()
        client.compact_conversation = AsyncMock(
            return_value={"messages": server_msgs}
        )
        msgs = _make_messages(5, chars_each=500)
        result = await compact_session(
            msgs, strategy="summarize", client=client, session_id="test-sid"
        )
        assert result.server_used is True
        assert result.messages == server_msgs

    @pytest.mark.asyncio
    async def test_falls_back_to_trim_on_server_failure(self):
        client = MagicMock()
        client.compact_conversation = AsyncMock(side_effect=RuntimeError("unavailable"))
        msgs = _make_messages(10, chars_each=2000)
        result = await compact_session(
            msgs, strategy="summarize", client=client, session_id="x"
        )
        assert result.server_used is False
        assert result.strategy_used == "trim"

    @pytest.mark.asyncio
    async def test_falls_back_to_trim_when_no_client(self):
        msgs = _make_messages(10, chars_each=2000)
        result = await compact_session(msgs, strategy="summarize", client=None)
        assert result.strategy_used == "trim"
        assert result.server_used is False

    @pytest.mark.asyncio
    async def test_falls_back_to_trim_on_empty_server_response(self):
        client = MagicMock()
        client.compact_conversation = AsyncMock(return_value={"messages": []})
        msgs = _make_messages(5, chars_each=500)
        result = await compact_session(msgs, strategy="summarize", client=client)
        assert result.server_used is False
        assert result.strategy_used == "trim"


# ── MemoryWatcher ─────────────────────────────────────────────────────────────

class TestMemoryWatcher:
    def test_no_warning_for_small_session(self):
        watcher = MemoryWatcher()
        msgs = _make_messages(2, chars_each=100)
        assert watcher.check(msgs) is None

    def test_warn_level_warning_emitted(self):
        watcher = MemoryWatcher(warn_tokens=100)
        msgs = [{"role": "user", "content": "a" * 500}]  # 125 tokens
        warning = watcher.check(msgs)
        assert warning is not None
        assert warning.level == "warn"

    def test_critical_level_warning_emitted(self):
        watcher = MemoryWatcher(warn_tokens=100, auto_compact_tokens=200)
        msgs = [{"role": "user", "content": "a" * 1000}]  # 250 tokens
        warning = watcher.check(msgs)
        assert warning is not None
        assert warning.level == "critical"

    def test_same_level_suppressed_on_second_call(self):
        watcher = MemoryWatcher(warn_tokens=100)
        msgs = [{"role": "user", "content": "a" * 500}]
        first = watcher.check(msgs)
        second = watcher.check(msgs)
        assert first is not None
        assert second is None  # suppressed — same level

    def test_reset_re_enables_warning(self):
        watcher = MemoryWatcher(warn_tokens=100)
        msgs = [{"role": "user", "content": "a" * 500}]
        watcher.check(msgs)
        watcher.reset()
        warning = watcher.check(msgs)
        assert warning is not None

    def test_should_auto_compact_false_for_small_session(self):
        watcher = MemoryWatcher()
        msgs = _make_messages(1, chars_each=100)
        assert watcher.should_auto_compact(msgs) is False

    def test_should_auto_compact_true_when_over_threshold(self):
        watcher = MemoryWatcher(auto_compact_tokens=100)
        msgs = [{"role": "user", "content": "a" * 500}]  # 125 tokens
        assert watcher.should_auto_compact(msgs) is True

    def test_should_block_false_below_hard_limit(self):
        watcher = MemoryWatcher()
        msgs = _make_messages(1, chars_each=100)
        assert watcher.should_block(msgs) is False

    def test_should_block_true_at_hard_limit(self):
        watcher = MemoryWatcher(hard_limit_tokens=100)
        msgs = [{"role": "user", "content": "a" * 500}]
        assert watcher.should_block(msgs) is True

    def test_warning_render_contains_markup(self):
        watcher = MemoryWatcher(warn_tokens=100)
        msgs = [{"role": "user", "content": "a" * 500}]
        warning = watcher.check(msgs)
        rendered = warning.render()
        assert "memory" in rendered.lower()
        assert len(rendered) > 10

    def test_level_change_emits_new_warning(self):
        watcher = MemoryWatcher(warn_tokens=100, auto_compact_tokens=200)
        small_warn = [{"role": "user", "content": "a" * 500}]  # 125 tokens → warn
        big_critical = [{"role": "user", "content": "a" * 1000}]  # 250 → critical
        first = watcher.check(small_warn)
        assert first is not None and first.level == "warn"
        second = watcher.check(big_critical)
        assert second is not None and second.level == "critical"
