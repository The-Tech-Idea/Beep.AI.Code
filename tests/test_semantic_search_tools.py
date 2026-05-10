"""Tests for beep.agent.tools.semantic_search adapter and tool classes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from beep.agent.tools.semantic_search import (
    FindRelatedCodeTool,
    SemanticSearchTool,
    SembleIndexAdapter,
    build_semble_tools,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk(file_path: str, start: int, end: int, content: str = "code") -> SimpleNamespace:
    return SimpleNamespace(file_path=file_path, start_line=start, end_line=end, content=content)


def _result(
    file_path: str,
    start: int,
    end: int,
    content: str = "code",
    score: float = 0.9,
) -> SimpleNamespace:
    chunk = _chunk(file_path, start, end, content)
    return SimpleNamespace(chunk=chunk, score=score, source=SimpleNamespace(value="hybrid"))


def _make_fake_index(
    *,
    results: list[Any] | None = None,
    related_results: list[Any] | None = None,
    chunks: list[Any] | None = None,
) -> MagicMock:
    idx = MagicMock()
    idx.search.return_value = results or []
    idx.find_related.return_value = related_results or []
    idx.chunks = chunks or []
    idx.stats = SimpleNamespace(indexed_files=5, total_chunks=20, languages={"python": 5})
    return idx


def _make_adapter(
    *,
    workspace_root: Path | None = None,
    results: list[Any] | None = None,
    related_results: list[Any] | None = None,
    chunks: list[Any] | None = None,
    semble_available: bool = True,
) -> SembleIndexAdapter:
    """Return a SembleIndexAdapter with a fake index loader."""
    fake_index = _make_fake_index(
        results=results, related_results=related_results, chunks=chunks
    )

    def _loader(_root: Path) -> MagicMock:
        return fake_index

    def _semble_loader() -> type:
        if not semble_available:
            raise RuntimeError("Semble is not installed.")
        return object  # just needs to not raise

    adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=_loader)
    adapter._load_semble = _semble_loader  # type: ignore[attr-defined]
    return adapter


# ---------------------------------------------------------------------------
# SembleIndexAdapter.availability_report
# ---------------------------------------------------------------------------

def test_adapter_availability_report_available() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        fake_index = _make_fake_index()
        adapter = SembleIndexAdapter(
            workspace_root=root,
            index_loader=lambda _: fake_index,
        )
        # prime cache by running a search so cached_index is set
        adapter._get_index(root)
        report = adapter.availability_report()
        # The loader will raise ImportError if semble is not actually installed.
        # We only check structural keys — not `available` since semble may not be present.
        assert "workspace_root" in report
        assert "cached" in report


def test_adapter_returns_cached_index_on_second_call() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        call_count = {"n": 0}

        def counting_loader(_root: Path) -> MagicMock:
            call_count["n"] += 1
            return _make_fake_index()

        adapter = SembleIndexAdapter(workspace_root=root, index_loader=counting_loader)
        adapter._get_index(root)
        adapter._get_index(root)
        assert call_count["n"] == 1


def test_adapter_rebuilds_index_on_different_root() -> None:
    with (
        tempfile.TemporaryDirectory() as td1,
        tempfile.TemporaryDirectory() as td2,
    ):
        root1 = Path(td1).resolve()
        root2 = Path(td2).resolve()
        call_count = {"n": 0}

        def counting_loader(_root: Path) -> MagicMock:
            call_count["n"] += 1
            return _make_fake_index()

        adapter = SembleIndexAdapter(workspace_root=root1, index_loader=counting_loader)
        adapter._get_index(root1)
        adapter._get_index(root2)
        assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# SembleIndexAdapter.search
# ---------------------------------------------------------------------------

def test_adapter_search_passes_query_and_top_k() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        fake_index = _make_fake_index(results=[_result("a.py", 1, 5)])
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        results = adapter.search(
            query="find me", path=None, top_k=3, mode="hybrid",
            filter_languages=None, filter_paths=None,
        )
        fake_index.search.assert_called_once()
        call_kwargs = fake_index.search.call_args[1]
        assert call_kwargs["top_k"] == 3
        assert call_kwargs["mode"] == "hybrid"
        assert len(results) == 1


def test_adapter_search_normalizes_filter_paths() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        fake_index = _make_fake_index()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        adapter.search(
            query="q",
            path=None,
            top_k=5,
            mode="hybrid",
            filter_languages=None,
            filter_paths=["src/a.py"],
        )
        call_kwargs = fake_index.search.call_args[1]
        assert call_kwargs["filter_paths"] == ["src/a.py"]


def test_adapter_search_raises_outside_workspace() -> None:
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        root = Path(td1).resolve()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: _make_fake_index())
        with pytest.raises(ValueError, match="outside workspace"):
            adapter.search(
                query="q",
                path=str(td2),
                top_k=5,
                mode="hybrid",
                filter_languages=None,
                filter_paths=None,
            )


# ---------------------------------------------------------------------------
# SembleIndexAdapter.find_related
# ---------------------------------------------------------------------------

def test_adapter_find_related_returns_results() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        anchor_chunk = _chunk("a.py", 1, 10)
        fake_index = _make_fake_index(
            related_results=[_result("b.py", 1, 5)],
            chunks=[anchor_chunk],
        )
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        results = adapter.find_related(file_path="a.py", line=5, path=None, top_k=3)
        fake_index.find_related.assert_called_once_with(anchor_chunk, top_k=3)
        assert len(results) == 1


def test_adapter_find_related_raises_when_no_chunk() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        fake_index = _make_fake_index(chunks=[])
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        with pytest.raises(ValueError, match="No chunk found"):
            adapter.find_related(file_path="missing.py", line=1, path=None, top_k=5)


# ---------------------------------------------------------------------------
# SemanticSearchTool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_tool_success() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        fake_results = [_result("src/a.py", 1, 10, content="def foo(): pass")]
        fake_index = _make_fake_index(results=fake_results)
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        tool = SemanticSearchTool(adapter)
        result = await tool.execute(query="foo function")
        assert result.success is True
        assert "src/a.py" in result.output


@pytest.mark.asyncio
async def test_semantic_search_tool_empty_query_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: _make_fake_index())
        tool = SemanticSearchTool(adapter)
        result = await tool.execute(query="")
        assert result.success is False
        assert "empty" in result.error.lower()


@pytest.mark.asyncio
async def test_semantic_search_tool_no_results() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: _make_fake_index())
        tool = SemanticSearchTool(adapter)
        result = await tool.execute(query="nonexistent symbol xyz")
        assert result.success is True
        assert "No results" in result.output


def test_semantic_search_tool_name() -> None:
    adapter = SembleIndexAdapter()
    tool = SemanticSearchTool(adapter)
    assert tool.name == "semantic_search"


def test_semantic_search_tool_is_read_only_safe() -> None:
    adapter = SembleIndexAdapter()
    tool = SemanticSearchTool(adapter)
    assert tool.read_only_safe is True


def test_semantic_search_tool_category_is_search() -> None:
    adapter = SembleIndexAdapter()
    tool = SemanticSearchTool(adapter)
    assert tool.category == "search"


# ---------------------------------------------------------------------------
# FindRelatedCodeTool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_related_tool_success() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        anchor = _chunk("src/a.py", 1, 10)
        fake_results = [_result("src/b.py", 5, 15, content="class Bar: pass")]
        fake_index = _make_fake_index(related_results=fake_results, chunks=[anchor])
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        tool = FindRelatedCodeTool(adapter)
        result = await tool.execute(file_path="src/a.py", line=5)
        assert result.success is True
        assert "src/b.py" in result.output


@pytest.mark.asyncio
async def test_find_related_tool_empty_file_path_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: _make_fake_index())
        tool = FindRelatedCodeTool(adapter)
        result = await tool.execute(file_path="", line=1)
        assert result.success is False


@pytest.mark.asyncio
async def test_find_related_tool_invalid_line_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: _make_fake_index())
        tool = FindRelatedCodeTool(adapter)
        result = await tool.execute(file_path="src/a.py", line="not-a-number")
        assert result.success is False


def test_find_related_tool_name() -> None:
    adapter = SembleIndexAdapter()
    tool = FindRelatedCodeTool(adapter)
    assert tool.name == "find_related_code"


def test_find_related_tool_is_read_only_safe() -> None:
    adapter = SembleIndexAdapter()
    tool = FindRelatedCodeTool(adapter)
    assert tool.read_only_safe is True


# ---------------------------------------------------------------------------
# build_semble_tools
# ---------------------------------------------------------------------------

def test_build_semble_tools_returns_pair() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        fake_index = _make_fake_index()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        search_tool, related_tool = build_semble_tools(workspace_root=root, adapter=adapter)
        assert search_tool.name == "semantic_search"
        assert related_tool.name == "find_related_code"


def test_build_semble_tools_share_same_adapter() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        fake_index = _make_fake_index()
        adapter = SembleIndexAdapter(workspace_root=root, index_loader=lambda _: fake_index)
        search_tool, related_tool = build_semble_tools(workspace_root=root, adapter=adapter)
        # Both tools must use the same adapter instance.
        assert search_tool._adapter is related_tool._adapter  # type: ignore[attr-defined]
