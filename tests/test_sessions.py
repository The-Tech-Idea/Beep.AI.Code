"""Tests for session history."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from beep.sessions.history import (
    create_session_id,
    delete_session,
    list_sessions,
    load_session,
    save_message,
)


class TestSessionHistory:
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                sid = "test-001"
                save_message(sid, {"role": "user", "content": "hello"})
                save_message(sid, {"role": "assistant", "content": "hi"})

                messages = load_session(sid)
                assert len(messages) == 2
                assert messages[0]["role"] == "user"
                assert messages[1]["role"] == "assistant"

    def test_load_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                assert load_session("nonexistent") == []

    def test_delete_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                sid = "test-del"
                save_message(sid, {"role": "user", "content": "test"})
                assert delete_session(sid) is True
                assert load_session(sid) == []

    def test_delete_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                assert delete_session("nonexistent") is False

    def test_list_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                save_message("sess-1", {"role": "user", "content": "msg1"})
                save_message("sess-2", {"role": "user", "content": "msg2"})

                sessions = list_sessions()
                assert len(sessions) == 2
                ids = {s.session_id for s in sessions}
                assert "sess-1" in ids
                assert "sess-2" in ids

    def test_list_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                assert list_sessions() == []

    def test_list_sessions_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                save_message("meta-test", {"role": "user", "content": "test"})
                sessions = list_sessions()
                assert len(sessions) == 1
                s = sessions[0]
                assert s.session_id == "meta-test"
                assert s.message_count == 1
                assert s.created_at is not None

    def test_skip_corrupt_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                path = history_dir / "corrupt.jsonl"
                history_dir.mkdir(parents=True, exist_ok=True)
                path.write_text("not json\n", encoding="utf-8")
                messages = load_session("corrupt")
                assert messages == []

    def test_create_session_id(self) -> None:
        sid = create_session_id()
        assert "T" in sid
        assert len(sid) > 10

    def test_multiple_messages_same_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                sid = "multi-msg"
                for i in range(5):
                    save_message(sid, {"role": "user", "content": f"msg {i}"})

                messages = load_session(sid)
                assert len(messages) == 5

    def test_load_legacy_session_file_migrates_schema_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            history_dir = Path(td) / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            path = history_dir / "legacy.jsonl"
            path.write_text(
                json.dumps({"timestamp": "2026-01-01T00:00:00+00:00", "role": "user", "content": "hello"}) + "\n",
                encoding="utf-8",
            )

            with patch("beep.sessions.history.HISTORY_DIR", history_dir):
                messages = load_session("legacy")

            assert messages == [{"role": "user", "content": "hello"}]
            migrated_lines = path.read_text(encoding="utf-8").splitlines()
            assert len(migrated_lines) == 2
            schema_entry = json.loads(migrated_lines[0])
            assert schema_entry["role"] == "meta"
            assert schema_entry["kind"] == "session_history_schema"
            assert schema_entry["schema_version"] == 1
