"""Tests for chat context and context window management."""

from __future__ import annotations

import tempfile
from pathlib import Path

from beep.chat.context import ChatContext


class TestChatContext:
    def test_pin_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "test.py"
            f.write_text("hello\n", encoding="utf-8")
            ctx = ChatContext(root)
            result = ctx.pin_file(Path("test.py"))
            assert "Pinned" in result
            assert f.resolve() in ctx.pinned_files

    def test_pin_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = ChatContext(Path(td))
            result = ctx.pin_file(Path("missing.py"))
            assert "not found" in result.lower()

    def test_pin_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "test.py"
            f.write_text("hello\n", encoding="utf-8")
            ctx = ChatContext(root)
            ctx.pin_file(Path("test.py"))
            result = ctx.pin_file(Path("test.py"))
            assert "Already pinned" in result

    def test_unpin_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "test.py"
            f.write_text("hello\n", encoding="utf-8")
            ctx = ChatContext(root)
            ctx.pin_file(Path("test.py"))
            result = ctx.unpin_file(Path("test.py"))
            assert "Unpinned" in result
            assert f.resolve() not in ctx.pinned_files

    def test_unpin_not_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = ChatContext(Path(td))
            result = ctx.unpin_file(Path("test.py"))
            assert "Not pinned" in result

    def test_build_context_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = ChatContext(Path(td))
            assert ctx.build_context() == ""

    def test_build_context_with_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "test.py"
            f.write_text("hello world\n", encoding="utf-8")
            ctx = ChatContext(root)
            ctx.pin_file(Path("test.py"))
            context = ctx.build_context()
            assert "Pinned Files" in context
            assert "hello world" in context

    def test_resolve_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "test.py"
            f.write_text("def main(): pass\n", encoding="utf-8")
            ctx = ChatContext(root)
            cleaned, included = ctx.resolve_mentions("what does @test.py do?")
            assert "def main(): pass" in cleaned
            assert "test.py" in included

    def test_resolve_mentions_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = ChatContext(Path(td))
            cleaned, included = ctx.resolve_mentions("what about @missing.py?")
            assert "not found" in cleaned.lower()
            assert included == []

    def test_resolve_mentions_no_at(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = ChatContext(Path(td))
            cleaned, included = ctx.resolve_mentions("just regular text")
            assert cleaned == "just regular text"
            assert included == []

    def test_resolve_multiple_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f1 = root / "a.py"
            f2 = root / "b.py"
            f1.write_text("file a\n", encoding="utf-8")
            f2.write_text("file b\n", encoding="utf-8")
            ctx = ChatContext(root)
            cleaned, included = ctx.resolve_mentions("compare @a.py and @b.py")
            assert "file a" in cleaned
            assert "file b" in cleaned
            assert len(included) == 2

    def test_context_with_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "large.py"
            f.write_text("x" * 60_000, encoding="utf-8")
            ctx = ChatContext(root)
            ctx.pin_file(Path("large.py"))
            context = ctx.build_context()
            assert "Pinned Files" in context
            assert "x" * 60_000 not in context
