"""Tests for new modules: completion, bookmarks, tasks, sandbox, security, websearch."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from beep.bookmarks.manager import BookmarkManager
from beep.completion.fuzzy import fuzzy_score
from beep.completion.path import complete_command
from beep.sandbox.executor import ExecutionResult
from beep.security.scanner import scan_file
from beep.tasks.manager import TaskManager, TaskStatus


class TestFuzzyScore:
    def test_empty_query(self) -> None:
        assert fuzzy_score("", "test.py") == 0

    def test_exact_match(self) -> None:
        assert fuzzy_score("test", "test.py") > 0

    def test_partial_match(self) -> None:
        assert fuzzy_score("ts", "test.py") > 0

    def test_no_match(self) -> None:
        assert fuzzy_score("xyz", "test.py") == 0

    def test_boundary_bonus(self) -> None:
        score_start = fuzzy_score("t", "test.py")
        score_mid = fuzzy_score("e", "test.py")
        assert score_start > score_mid


class TestCompleteCommand:
    def test_no_slash(self) -> None:
        assert complete_command("help", {"help": "Show help"}) == []

    def test_partial_match(self) -> None:
        cmds = {"help": "Show help", "hello": "Say hello"}
        result = complete_command("/he", cmds)
        assert "/help" in result
        assert "/hello" in result

    def test_exact_match(self) -> None:
        cmds = {"help": "Show help"}
        assert complete_command("/help", cmds) == ["/help"]

    def test_case_insensitive(self) -> None:
        cmds = {"Help": "Show help"}
        assert complete_command("/help", cmds) == ["/Help"]


class TestBookmarkManager:
    def test_load_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bm_file = Path(td) / "bm.json"
            with patch("beep.bookmarks.manager.BOOKMARKS_FILE", bm_file):
                mgr = BookmarkManager.load()
                assert mgr.bookmarks == []

    def test_add_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bm_file = Path(td) / "bm.json"
            with patch("beep.bookmarks.manager.BOOKMARKS_FILE", bm_file):
                mgr = BookmarkManager.load()
                mgr.add("main", Path(td) / "main.py")
                path = mgr.get("main")
                assert path == Path(td) / "main.py"

    def test_remove(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bm_file = Path(td) / "bm.json"
            with patch("beep.bookmarks.manager.BOOKMARKS_FILE", bm_file):
                mgr = BookmarkManager.load()
                mgr.add("test", Path(td) / "test.py")
                mgr.remove("test")
                assert mgr.get("test") is None

    def test_update_existing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bm_file = Path(td) / "bm.json"
            with patch("beep.bookmarks.manager.BOOKMARKS_FILE", bm_file):
                mgr = BookmarkManager.load()
                mgr.add("main", Path(td) / "old.py")
                mgr.add("main", Path(td) / "new.py")
                bookmarks = mgr.list_all()
                assert len(bookmarks) == 1
                assert bookmarks[0].path == str(Path(td) / "new.py")


class TestTaskManager:
    def test_list_empty(self) -> None:
        mgr = TaskManager()
        assert mgr.list_all() == []

    def test_get_nonexistent(self) -> None:
        mgr = TaskManager()
        assert mgr.get("nonexistent") is None

    def test_task_dataclass(self) -> None:
        from beep.tasks.manager import BackgroundTask
        task = BackgroundTask(id="abc123", name="test", command="echo hello")
        assert task.name == "test"
        assert task.command == "echo hello"
        assert task.status == TaskStatus.PENDING


class TestSecurityScanner:
    def test_scan_clean_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "clean.py"
            f.write_text("x = 1 + 2\n", encoding="utf-8")
            findings = scan_file(f)
            assert findings == []

    def test_scan_eval(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "unsafe.py"
            f.write_text("result = eval(user_input)\n", encoding="utf-8")
            findings = scan_file(f)
            assert any(finding.rule == "python-eval" for finding in findings)

    def test_scan_hardcoded_password(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "config.py"
            f.write_text('password = "secret123"\n', encoding="utf-8")
            findings = scan_file(f)
            assert any(finding.rule == "python-hardcoded-password" for finding in findings)

    def test_scan_js_innerhtml(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "app.js"
            f.write_text("el.innerHTML = userContent;\n", encoding="utf-8")
            findings = scan_file(f)
            assert any(finding.rule == "js-innerhtml" for finding in findings)


class TestExecutionResult:
    def test_success(self) -> None:
        result = ExecutionResult(success=True, stdout="hello", exit_code=0)
        assert result.success
        assert result.stdout == "hello"

    def test_error(self) -> None:
        result = ExecutionResult(success=False, stderr="error", exit_code=1)
        assert not result.success
        assert result.stderr == "error"
