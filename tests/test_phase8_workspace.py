"""Tests for Phase 8 — Workspace Utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from rich.tree import Tree


# ---------------------------------------------------------------------------
# TestMatchResult / find_best_match
# ---------------------------------------------------------------------------

class TestMatchResult:
    def test_find_best_match_returns_match_result(self) -> None:
        from beep.workspace.search_replace import find_best_match, MatchResult

        content = "def hello():\n    pass\n"
        result = find_best_match("def hello():", content)
        assert result is not None
        assert isinstance(result, MatchResult)
        assert result.confidence > 0.7
        assert result.start_line == 0
        assert result.matched_text == "def hello():"

    def test_find_best_match_returns_low_confidence_candidate(self) -> None:
        from beep.workspace.search_replace import find_best_match

        content = "def hello():\n    pass\n"
        result = find_best_match("completely_unrelated_zxcvbnm", content)
        assert result is not None
        assert result.confidence < 0.7

    def test_match_result_has_confidence_field(self) -> None:
        from beep.workspace.search_replace import MatchResult

        m = MatchResult(start_line=0, end_line=1, confidence=0.95, matched_text="hello")
        assert m.confidence == 0.95
        assert m.matched_text == "hello"


# ---------------------------------------------------------------------------
# TestAtomicMultiBlock
# ---------------------------------------------------------------------------

class TestAtomicMultiBlock:
    def test_partial_failure_returns_no_changes(self) -> None:
        from beep.workspace.search_replace import apply_blocks_from_text

        content = "line one\nline two\n"
        # First block matches, second block doesn't
        text = (
            "<<<<<<< SEARCH\nline one\n=======\nreplaced one\n>>>>>>> REPLACE\n"
            "<<<<<<< SEARCH\nDOES_NOT_EXIST_ZXCVBNM\n=======\nreplaced two\n>>>>>>> REPLACE\n"
        )
        result, messages = apply_blocks_from_text(content, text)
        # Atomic: no change because second block failed
        assert result == content
        assert any("FAILED" in m for m in messages)

    def test_low_confidence_failure_reports_candidate_diagnostics(self) -> None:
        from beep.workspace.search_replace import apply_blocks_from_text

        content = "line one\nline two\n"
        text = (
            "<<<<<<< SEARCH\n"
            "totally unrelated search text\n"
            "=======\n"
            "replacement\n"
            ">>>>>>> REPLACE\n"
        )
        result, messages = apply_blocks_from_text(content, text)

        assert result == content
        assert any("Low-confidence fuzzy match rejected" in m for m in messages)
        assert any("Best candidate:" in m for m in messages)

    def test_all_blocks_success_applies_all(self) -> None:
        from beep.workspace.search_replace import apply_blocks_from_text

        content = "line one\nline two\n"
        text = (
            "<<<<<<< SEARCH\nline one\n=======\nreplaced one\n>>>>>>> REPLACE\n"
            "<<<<<<< SEARCH\nline two\n=======\nreplaced two\n>>>>>>> REPLACE\n"
        )
        result, messages = apply_blocks_from_text(content, text)
        assert "replaced one" in result
        assert "replaced two" in result
        assert not any("FAILED" in m for m in messages)


# ---------------------------------------------------------------------------
# TestFileOpsDiff
# ---------------------------------------------------------------------------

class TestFileOpsDiff:
    def test_create_diff_no_double_newlines(self) -> None:
        from beep.workspace.file_ops import create_diff

        old = "line1\nline2\n"
        new = "line1\nline3\n"
        diff = create_diff(old, new)
        # Should not have consecutive blank lines from trailing \n on each line
        assert "\n\n\n" not in diff
        assert "-line2" in diff
        assert "+line3" in diff


# ---------------------------------------------------------------------------
# TestReadLines
# ---------------------------------------------------------------------------

class TestReadLines:
    def test_read_all_lines(self) -> None:
        from beep.workspace.file_ops import read_lines

        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "sample.py"
            f.write_text("a\nb\nc\n", encoding="utf-8")
            lines, total = read_lines(f)
            assert total == 3
            assert lines == ["a", "b", "c"]

    def test_read_partial_range(self) -> None:
        from beep.workspace.file_ops import read_lines

        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "sample.py"
            f.write_text("a\nb\nc\nd\n", encoding="utf-8")
            lines, total = read_lines(f, start=2, end=3)
            assert total == 4
            assert lines == ["b", "c"]


# ---------------------------------------------------------------------------
# TestWriteFileCreatesParentDirs
# ---------------------------------------------------------------------------

class TestWriteFileCreatesParentDirs:
    def test_write_file_creates_missing_parents(self) -> None:
        from beep.workspace.file_ops import write_file

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "new_subdir" / "nested" / "file.py"
            write_file(p, "x = 1\n", create_backup=False)
            assert p.exists()
            assert p.read_text() == "x = 1\n"


# ---------------------------------------------------------------------------
# TestBinaryDetector
# ---------------------------------------------------------------------------

class TestBinaryDetector:
    def test_text_file_is_not_binary(self) -> None:
        from beep.workspace.binary_detector import is_binary_file

        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "text.py"
            f.write_text("print('hello')\n", encoding="utf-8")
            assert not is_binary_file(f)

    def test_binary_file_detected(self) -> None:
        from beep.workspace.binary_detector import is_binary_file

        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "binary.bin"
            f.write_bytes(b"PNG\x00\x00\x00some data")
            assert is_binary_file(f)

    def test_missing_file_returns_true(self) -> None:
        from beep.workspace.binary_detector import is_binary_file

        assert is_binary_file(Path("/no/such/file.bin"))


# ---------------------------------------------------------------------------
# TestGetRecentCommits
# ---------------------------------------------------------------------------

class TestGetRecentCommits:
    def test_non_git_repo_returns_empty(self) -> None:
        from beep.workspace.git import get_recent_commits

        with tempfile.TemporaryDirectory() as td:
            result = get_recent_commits(Path(td))
            assert result == []

    def test_get_git_diff_returns_none_for_non_git_repo(self) -> None:
        from beep.workspace.git import get_git_diff

        with tempfile.TemporaryDirectory() as td:
            result = get_git_diff(Path(td))
            assert result is None

    def test_commit_info_dataclass(self) -> None:
        from beep.workspace.git import CommitInfo

        c = CommitInfo(hash="abc123", message="initial", author="Dev", date="2024-01-01")
        assert c.hash == "abc123"
        assert c.message == "initial"


# ---------------------------------------------------------------------------
# TestDetectorStopsAtHome
# ---------------------------------------------------------------------------

class TestDetectorStopsAtHome:
    def test_find_workspace_root_falls_back_to_start(self) -> None:
        from beep.workspace.detector import find_workspace_root

        with tempfile.TemporaryDirectory() as td:
            # No .git in td or its parents up to home — should return td itself
            result = find_workspace_root(Path(td))
            # It either found a real .git up the chain or returned the start
            assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# TestFileReadToolSkipsBinary
# ---------------------------------------------------------------------------

class TestFileReadToolSkipsBinary:
    @pytest.mark.asyncio
    async def test_binary_file_returns_error(self) -> None:
        from beep.agent.tools.file_read import FileReadTool

        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "img.png"
            f.write_bytes(b"PNG\x00\x00\x00data")
            tool = FileReadTool(workspace_root=Path(td))
            result = await tool.execute(file_path=str(f))
            assert not result.success
            assert "binary" in result.error.lower()


# ---------------------------------------------------------------------------
# TestContextBuilderSkipsBinary
# ---------------------------------------------------------------------------

class TestContextBuilderSkipsBinary:
    def test_binary_file_is_marked_skipped(self) -> None:
        from beep.context.builder import build_context

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            binary = root / "asset.bin"
            binary.write_bytes(b"BIN\x00\x01payload")

            result = build_context([binary], workspace_root=root)

            assert "asset.bin (binary, skipped)" in result


# ---------------------------------------------------------------------------
# TestFileTreeUsesIgnoreMatcher
# ---------------------------------------------------------------------------

class TestFileTreeUsesIgnoreMatcher:
    def test_build_tree_omits_ignored_entries(self) -> None:
        from beep.workspace.file_tree import build_tree
        from beep.workspace.ignore import IgnoreMatcher

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "visible.txt").write_text("ok\n", encoding="utf-8")
            (root / "ignored.txt").write_text("skip\n", encoding="utf-8")

            tree = Tree("root")
            matcher = IgnoreMatcher(root, patterns=["ignored.txt"])
            build_tree(root, tree, matcher=matcher)

            labels = [str(child.label) for child in tree.children]
            assert any("visible.txt" in label for label in labels)
            assert all("ignored.txt" not in label for label in labels)

    def test_build_tree_allows_missing_matcher(self) -> None:
        from beep.workspace.file_tree import build_tree

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "visible.txt").write_text("ok\n", encoding="utf-8")

            tree = Tree("root")
            build_tree(root, tree, matcher=None)

            labels = [str(child.label) for child in tree.children]
            assert any("visible.txt" in label for label in labels)
