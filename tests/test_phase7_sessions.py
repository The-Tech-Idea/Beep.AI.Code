"""Tests for Phase 7 — Session History & Compaction."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.fake_history_graph_runtime import (
    HistoryFakeAsyncSqliteSaver,
    HistoryFakeStateGraph,
    HistoryFakeToolNode,
)

from beep.sessions.history import (
    SessionSummary,
    _relative_time,
    _parse_timestamp,
    append_message,
    create_session_id,
    estimate_tokens,
    export_session,
    list_sessions,
    load_session,
    maybe_compact_session,
    replace_session,
    search_sessions,
)


# ---------------------------------------------------------------------------
# TestSessionSummary
# ---------------------------------------------------------------------------

class TestSessionSummary:
    def test_dataclass_fields(self) -> None:
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        s = SessionSummary(
            session_id="abc",
            created_at=dt,
            message_count=5,
            last_message_preview="hello world",
        )
        assert s.session_id == "abc"
        assert s.created_at == dt
        assert s.message_count == 5
        assert s.last_message_preview == "hello world"

    def test_create_session_id_has_timestamp_prefix(self) -> None:
        sid = create_session_id()
        # new format: YYYYMMDDTHHMMSS-xxxxxx
        assert "T" in sid
        assert len(sid) > 10


# ---------------------------------------------------------------------------
# TestRelativeTime
# ---------------------------------------------------------------------------

class TestRelativeTime:
    def test_none_returns_unknown(self) -> None:
        assert _relative_time(None) == "unknown"

    def test_recent_returns_just_now(self) -> None:
        dt = datetime.now(tz=timezone.utc)
        assert _relative_time(dt) == "just now"

    def test_minutes_ago(self) -> None:
        from datetime import timedelta
        dt = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
        result = _relative_time(dt)
        assert "minute" in result

    def test_hours_ago(self) -> None:
        from datetime import timedelta
        dt = datetime.now(tz=timezone.utc) - timedelta(hours=3)
        result = _relative_time(dt)
        assert "hour" in result

    def test_days_ago(self) -> None:
        from datetime import timedelta
        dt = datetime.now(tz=timezone.utc) - timedelta(days=2)
        result = _relative_time(dt)
        assert "day" in result


# ---------------------------------------------------------------------------
# TestParseTimestamp
# ---------------------------------------------------------------------------

class TestParseTimestamp:
    def test_valid_iso(self) -> None:
        dt = _parse_timestamp("2024-06-15T12:00:00")
        assert dt is not None
        assert dt.year == 2024

    def test_none_input(self) -> None:
        assert _parse_timestamp(None) is None

    def test_invalid_string(self) -> None:
        assert _parse_timestamp("not-a-date") is None


# ---------------------------------------------------------------------------
# TestAppendMessage / AtomicWrite
# ---------------------------------------------------------------------------

class TestAppendMessage:
    def test_append_creates_file_and_flushes(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("test-sess", {"role": "user", "content": "hello"})
                f = Path(td) / "test-sess.jsonl"
                assert f.exists()
                lines = f.read_text().strip().splitlines()
                assert len(lines) == 2
                schema_entry = json.loads(lines[0])
                assert schema_entry["role"] == "meta"
                assert schema_entry["kind"] == "session_history_schema"
                entry = json.loads(lines[1])
                assert entry["role"] == "user"
                assert entry["content"] == "hello"
                assert "timestamp" in entry
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    def test_replace_session_is_atomic(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                replace_session(
                    "sess2",
                    [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
                )
                loaded = load_session("sess2")
                assert len(loaded) == 2
                assert loaded[0]["role"] == "user"
                assert not (Path(td) / "sess2.tmp").exists()
            finally:
                hist_mod.HISTORY_DIR = orig_dir


# ---------------------------------------------------------------------------
# TestListSessions — returns SessionSummary objects
# ---------------------------------------------------------------------------

class TestListSessions:
    def test_returns_session_summary_objects(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("sess-a", {"role": "user", "content": "hello"})
                results = list_sessions()
                assert results
                assert isinstance(results[0], SessionSummary)
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    def test_meta_messages_excluded_from_count(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("sess-b", {"role": "user", "content": "q"})
                append_message("sess-b", {"role": "assistant", "content": "a"})
                append_message("sess-b", {"role": "meta", "reason": "completed"})
                results = list_sessions()
                r = next(s for s in results if s.session_id == "sess-b")
                assert r.message_count == 2  # meta not counted
            finally:
                hist_mod.HISTORY_DIR = orig_dir


# ---------------------------------------------------------------------------
# TestExportSession
# ---------------------------------------------------------------------------

class TestExportSession:
    def test_export_markdown(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("e1", {"role": "user", "content": "hi"})
                append_message("e1", {"role": "assistant", "content": "hello"})
                md = export_session("e1", format="md")
                assert "## User" in md
                assert "## Assistant" in md
                assert "hi" in md
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    def test_export_json(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("e2", {"role": "user", "content": "ping"})
                out = export_session("e2", format="json")
                parsed = json.loads(out)
                assert isinstance(parsed, list)
                assert parsed[0]["content"] == "ping"
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    def test_export_missing_session_returns_empty(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                assert export_session("no-such", format="md") == ""
            finally:
                hist_mod.HISTORY_DIR = orig_dir


# ---------------------------------------------------------------------------
# TestSearchSessions
# ---------------------------------------------------------------------------

class TestSearchSessions:
    def test_finds_matching_session(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("s1", {"role": "user", "content": "refactor the auth module"})
                append_message("s2", {"role": "user", "content": "unrelated topic"})
                results = search_sessions("auth module")
                ids = [r.session_id for r in results]
                assert "s1" in ids
                assert "s2" not in ids
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    def test_case_insensitive(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("s3", {"role": "user", "content": "Fix the BUG in login"})
                results = search_sessions("bug in login")
                assert any(r.session_id == "s3" for r in results)
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    def test_no_results_when_no_match(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("s4", {"role": "user", "content": "hello world"})
                results = search_sessions("zxcvbnm_unlikely")
                assert results == []
            finally:
                hist_mod.HISTORY_DIR = orig_dir


# ---------------------------------------------------------------------------
# TestMaybeCompactSession
# ---------------------------------------------------------------------------

class TestMaybeCompactSession:
    def test_no_compact_below_threshold(self) -> None:
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        from beep.sessions import history as hist_mod
        orig = hist_mod._COMPACTION_CHECK_INTERVAL
        hist_mod._COMPACTION_CHECK_INTERVAL = 1
        hist_mod._append_counter["compact-test"] = 0
        try:
            result = maybe_compact_session("compact-test", messages, threshold=100_000)
            assert result is messages  # no-op, tokens well below threshold
        finally:
            hist_mod._COMPACTION_CHECK_INTERVAL = orig

    def test_compacts_when_over_threshold(self) -> None:
        from beep.sessions import history as hist_mod

        orig_interval = hist_mod._COMPACTION_CHECK_INTERVAL
        hist_mod._COMPACTION_CHECK_INTERVAL = 1
        hist_mod._append_counter["compact-test2"] = 0
        try:
            big_content = "x" * 10_000  # ~2500 tokens each
            messages = [{"role": "system", "content": "sys"}] + [
                {"role": "user", "content": big_content} for _ in range(30)
            ]
            result = maybe_compact_session("compact-test2", messages, threshold=100)
            assert len(result) <= 21  # system + up to 20
            assert result[0]["role"] == "system"
        finally:
            hist_mod._COMPACTION_CHECK_INTERVAL = orig_interval

    def test_chat_session_save_rewrites_history_when_compaction_triggers(self) -> None:
        from types import SimpleNamespace

        from beep.chat.repl import ChatSession

        original_messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "answer"},
        ]
        compacted_messages = [
            {"role": "system", "content": "sys"},
            {"role": "assistant", "content": "summary"},
        ]
        fake_session = SimpleNamespace(
            _session_id="compact-chat-session",
            _messages=original_messages,
        )

        with (
            patch("beep.chat.repl.save_message") as save_mock,
            patch(
                "beep.chat.repl.maybe_compact_session",
                return_value=compacted_messages,
            ) as compact_mock,
            patch("beep.chat.repl.replace_session") as replace_mock,
        ):
            ChatSession._save(fake_session, "assistant", "answer")

        save_mock.assert_called_once_with(
            "compact-chat-session",
            {"role": "assistant", "content": "answer"},
        )
        assert compact_mock.call_args.args[0] == "compact-chat-session"
        assert compact_mock.call_args.args[1] is original_messages
        assert fake_session._messages == compacted_messages
        replace_mock.assert_called_once_with("compact-chat-session", compacted_messages)


# ---------------------------------------------------------------------------
# TestEstimateTokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_empty_messages(self) -> None:
        assert estimate_tokens([]) == 0

    def test_approximate(self) -> None:
        messages = [{"role": "user", "content": "a" * 400}]
        assert estimate_tokens(messages) == 100  # 400 / 4


# ---------------------------------------------------------------------------
# TestGraphRunPersistsHistory
# ---------------------------------------------------------------------------

class TestGraphRunPersistsHistory:
    async def _run_history_graph(self, *, goal: str, session_id: str, workspace_root: Path) -> None:
        from beep.agent.graph import run_graph

        with patch(
            "beep.agent.graph._load_langgraph_dependencies",
            return_value=(
                "__start__",
                "__end__",
                HistoryFakeStateGraph,
                HistoryFakeAsyncSqliteSaver,
                HistoryFakeToolNode,
            ),
        ):
            await run_graph(
                goal=goal,
                backend=MagicMock(),
                tools=[],
                workspace_root=workspace_root,
                system_prompt="system prompt",
                workspace_rules=[],
                session_id=session_id,
                max_steps=5,
                max_tool_calls_per_step=3,
                max_tool_calls_total=10,
                step_timeout=30.0,
                max_repeated_calls=3,
                max_consecutive_failures=2,
                max_tool_output_chars=4000,
                auto_approve=True,
            )

    @pytest.mark.asyncio
    async def test_run_graph_writes_meta_sentinel(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                await self._run_history_graph(
                    goal="do something",
                    session_id="agent-test-1",
                    workspace_root=Path(td),
                )
                f = Path(td) / "agent-test-1.jsonl"
                assert f.exists()
                lines = [json.loads(ln) for ln in f.read_text().strip().splitlines()]
                roles = [ln.get("role") for ln in lines]
                assert "meta" in roles
                meta = next(ln for ln in lines if ln.get("role") == "meta" and "reason" in ln)
                assert "reason" in meta
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    @pytest.mark.asyncio
    async def test_run_graph_writes_goal_message(self) -> None:
        from beep.sessions import history as hist_mod

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                await self._run_history_graph(
                    goal="my specific goal",
                    session_id="agent-test-2",
                    workspace_root=Path(td),
                )
                f = Path(td) / "agent-test-2.jsonl"
                lines = [json.loads(ln) for ln in f.read_text().strip().splitlines()]
                user_lines = [ln for ln in lines if ln.get("role") == "user"]
                assert any("goal" in ln.get("content", "").lower() for ln in user_lines)
            finally:
                hist_mod.HISTORY_DIR = orig_dir


# ---------------------------------------------------------------------------
# TestSessionsCommandSummary
# ---------------------------------------------------------------------------

class TestSessionsCommandSummary:
    @pytest.mark.asyncio
    async def test_sessions_list_shows_relative_time(self) -> None:
        from beep.sessions import history as hist_mod
        from beep.chat.commands.session import SessionsCommand

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("x123", {"role": "user", "content": "hello"})
                cmd = SessionsCommand()
                await cmd.execute("list", {})
                # No exception = success; table rendered to rich Console
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    @pytest.mark.asyncio
    async def test_sessions_export_md(self) -> None:
        from beep.sessions import history as hist_mod
        from beep.chat.commands.session import SessionsCommand

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                append_message("xexp1", {"role": "user", "content": "test content"})
                cmd = SessionsCommand()
                await cmd.execute("export xexp1 md", {})
                # No exception = success
            finally:
                hist_mod.HISTORY_DIR = orig_dir

    @pytest.mark.asyncio
    async def test_sessions_export_unknown_format(self) -> None:
        from beep.sessions import history as hist_mod
        from beep.chat.commands.session import SessionsCommand

        orig_dir = hist_mod.HISTORY_DIR
        with tempfile.TemporaryDirectory() as td:
            hist_mod.HISTORY_DIR = Path(td)
            try:
                cmd = SessionsCommand()
                # Should not raise
                await cmd.execute("export xid xml", {})
            finally:
                hist_mod.HISTORY_DIR = orig_dir
