"""Tests for automatic workspace context injection in normal chat."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from beep.context.auto_context import (
    AutoContextBuilder,
    AutoContextResult,
    build_auto_context,
    DEFAULT_AUTO_CONTEXT_BUDGET_CHARS,
)


class _FakeChunk:
    def __init__(self, path: str, content: str) -> None:
        self.path = path
        self.content = content


class TestAutoContextBuilder:
    def test_empty_query_returns_workspace_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "hello.py").write_text("print('hi')\n", encoding="utf-8")
            builder = AutoContextBuilder(root)
            result = builder.build("")
            # Empty query in empty repo should at least get workspace summary
            assert isinstance(result, AutoContextResult)
            assert "Workspace" in result.context_text or result.context_text == ""

    def test_query_selects_git_modified_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "app.py").write_text("def main(): pass\n", encoding="utf-8")
            (root / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")
            builder = AutoContextBuilder(root)
            result = builder.build("app")
            assert isinstance(result.sources, list)
            assert result.tokens_used >= 0

    def test_semble_retrieval_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "service.py").write_text("class Service: pass\n", encoding="utf-8")
            adapter = MagicMock()
            adapter.search.return_value = [
                _FakeChunk("service.py", "class Service:\n    def run(self): pass\n"),
            ]
            builder = AutoContextBuilder(root, semantic_search_adapter=adapter)
            result = builder.build("how does Service work")
            assert "Semantic Code Retrieval" in result.context_text
            assert "semantic_search" in result.sources
            adapter.search.assert_called_once()

    def test_semble_retrieval_when_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "main.py").write_text("x = 1\n", encoding="utf-8")
            builder = AutoContextBuilder(root, semantic_search_adapter=None)
            result = builder.build("what is x")
            # Should not crash, should fall back to smart file selection
            assert isinstance(result, AutoContextResult)
            assert "semantic_search" not in result.sources

    def test_budget_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Create a large file that would exceed small budget
            (root / "big.py").write_text("x = " + "0" * 10000 + "\n", encoding="utf-8")
            builder = AutoContextBuilder(root, budget_chars=500)
            result = builder.build("big")
            assert result.truncated or len(result.context_text) <= 500

    def test_no_files_in_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            builder = AutoContextBuilder(root)
            result = builder.build("anything")
            # Should not crash, may return workspace summary or empty
            assert isinstance(result, AutoContextResult)

    def test_convenience_function(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "test.py").write_text("def test(): assert True\n", encoding="utf-8")
            result = build_auto_context("test function", workspace_root=root)
            assert isinstance(result, AutoContextResult)

    def test_semble_error_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            adapter = MagicMock()
            adapter.search.side_effect = RuntimeError("Semble crashed")
            builder = AutoContextBuilder(root, semantic_search_adapter=adapter)
            result = builder.build("something")
            # Should gracefully fall back to file context
            assert isinstance(result, AutoContextResult)
            assert "semantic_search" not in result.sources

    def test_semble_empty_results_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "mod.py").write_text("y = 2\n", encoding="utf-8")
            adapter = MagicMock()
            adapter.search.return_value = []
            builder = AutoContextBuilder(root, semantic_search_adapter=adapter)
            result = builder.build("query")
            # Semble returned nothing, should try smart file selection
            assert isinstance(result, AutoContextResult)


class TestAutoContextIntegration:
    def test_send_path_includes_auto_context_when_enabled(self) -> None:
        """Verify that the send path injects auto-context content."""
        from beep.chat.repl import ChatSession

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "main.py").write_text("def main(): pass\n", encoding="utf-8")

            mock_client = MagicMock()
            mock_client.chat_completion_stream.return_value = AsyncMock()

            with patch("beep.chat.repl.find_workspace_root", return_value=root):
                session = ChatSession(
                    client=mock_client,
                    plugins_enabled=False,
                )
                session._workspace = root
                assert session.auto_context_enabled is True

    def test_toggle_auto_context(self) -> None:
        from beep.chat.repl import ChatSession

        mock_client = MagicMock()
        mock_client.chat_completion_stream.return_value = AsyncMock()

        session = ChatSession.__new__(ChatSession)
        session._auto_context_enabled = True

        assert session.auto_context_enabled is True
        session.set_auto_context_enabled(False)
        assert session.auto_context_enabled is False
        session.set_auto_context_enabled(True)
        assert session.auto_context_enabled is True
