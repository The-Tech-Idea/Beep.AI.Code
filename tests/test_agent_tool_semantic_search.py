"""Unit tests for Semble-backed semantic search tools."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from beep.agent.tools.semantic_search import (
    FindRelatedCodeTool,
    SemanticSearchTool,
    SembleIndexAdapter,
)


@dataclass(frozen=True)
class _FakeChunk:
    file_path: str
    start_line: int
    end_line: int
    content: str
    language: str | None = None


class _FakeIndex:
    def __init__(self) -> None:
        self.chunks = [
            _FakeChunk(
                file_path="src/foo.py",
                start_line=10,
                end_line=16,
                content="def foo():\n    return 1\n",
                language="python",
            ),
            _FakeChunk(
                file_path="src/bar.py",
                start_line=20,
                end_line=26,
                content="def bar():\n    return foo()\n",
                language="python",
            ),
        ]
        self.search_calls: list[dict[str, object]] = []
        self.find_related_calls: list[dict[str, object]] = []

    def search(
        self,
        query: str,
        *,
        top_k: int,
        mode: str,
        filter_languages: list[str] | None,
        filter_paths: list[str] | None,
    ) -> list[SimpleNamespace]:
        self.search_calls.append(
            {
                "query": query,
                "top_k": top_k,
                "mode": mode,
                "filter_languages": filter_languages,
                "filter_paths": filter_paths,
            }
        )
        return [
            SimpleNamespace(
                chunk=self.chunks[0],
                score=0.912,
                source=SimpleNamespace(value=mode),
            )
        ]

    def find_related(self, source: _FakeChunk, *, top_k: int) -> list[SimpleNamespace]:
        self.find_related_calls.append({"source": source, "top_k": top_k})
        return [
            SimpleNamespace(
                chunk=self.chunks[1],
                score=0.801,
                source=SimpleNamespace(value="semantic"),
            )
        ]


@pytest.mark.asyncio
async def test_semantic_search_formats_results_and_forwards_modes_and_filters() -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        fake_index = _FakeIndex()
        adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=lambda _root: fake_index)
        tool = SemanticSearchTool(adapter)

        result = await tool.execute(
            query="find foo",
            mode="semantic",
            top_k=3,
            filter_languages=["python"],
            filter_paths=[str(workspace_root / "src" / "foo.py")],
        )

    assert result.success
    assert "Search results for: 'find foo' (mode=semantic)" in result.output
    assert "src/foo.py:10-16" in result.output
    assert "score=0.912" in result.output
    assert fake_index.search_calls == [
        {
            "query": "find foo",
            "top_k": 3,
            "mode": "semantic",
            "filter_languages": ["python"],
            "filter_paths": ["src/foo.py"],
        }
    ]


@pytest.mark.asyncio
async def test_find_related_code_resolves_absolute_file_path_and_formats_output() -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        fake_index = _FakeIndex()
        adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=lambda _root: fake_index)
        tool = FindRelatedCodeTool(adapter)

        result = await tool.execute(
            file_path=str(workspace_root / "src" / "foo.py"),
            line=12,
            top_k=2,
        )

    assert result.success
    assert "Chunks related to" in result.output
    assert "src/bar.py:20-26" in result.output
    assert fake_index.find_related_calls[0]["source"] == fake_index.chunks[0]
    assert fake_index.find_related_calls[0]["top_k"] == 2


@pytest.mark.asyncio
async def test_find_related_code_returns_clear_error_when_chunk_missing() -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        fake_index = _FakeIndex()
        adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=lambda _root: fake_index)
        tool = FindRelatedCodeTool(adapter)

        result = await tool.execute(file_path="src/missing.py", line=1)

    assert not result.success
    assert "No chunk found" in (result.error or "")


@pytest.mark.asyncio
async def test_adapter_caches_index_across_tool_calls() -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        fake_index = _FakeIndex()
        loader_calls: list[Path] = []

        def loader(root: Path) -> _FakeIndex:
            loader_calls.append(root)
            return fake_index

        adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=loader)
        search_tool = SemanticSearchTool(adapter)
        related_tool = FindRelatedCodeTool(adapter)

        first = await search_tool.execute(query="foo")
        second = await related_tool.execute(file_path="src/foo.py", line=10)

    assert first.success
    assert second.success
    assert loader_calls == [workspace_root.resolve()]


@pytest.mark.asyncio
async def test_semantic_search_returns_clear_error_when_semble_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        adapter = SembleIndexAdapter(workspace_root=workspace_root)
        tool = SemanticSearchTool(adapter)
        monkeypatch.setattr(
            "beep.agent.tools.semantic_search._load_semble_index",
            lambda: (_ for _ in ()).throw(RuntimeError("Semble is not installed in the agent environment.")),
        )

        result = await tool.execute(query="foo")

    assert not result.success
    assert "Semble is not installed" in (result.error or "")


@pytest.mark.asyncio
async def test_semantic_search_rejects_invalid_mode() -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        fake_index = _FakeIndex()
        adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=lambda _root: fake_index)
        tool = SemanticSearchTool(adapter)

        result = await tool.execute(query="foo", mode="not-a-mode")

    assert not result.success
    assert "Invalid search mode" in (result.error or "")


def test_adapter_availability_report_includes_cached_index_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        fake_index = _FakeIndex()
        fake_index.stats = SimpleNamespace(indexed_files=2, total_chunks=7, languages={"python": 7})
        adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=lambda _root: fake_index)
        monkeypatch.setattr("beep.agent.tools.semantic_search._load_semble_index", lambda: object())

        adapter.search(
            query="foo",
            path=None,
            top_k=1,
            mode="hybrid",
            filter_languages=None,
            filter_paths=None,
        )
        report = adapter.availability_report()

    assert report["available"] is True
    assert report["cached"] is True
    assert report["stats"] == {
        "indexed_files": 2,
        "total_chunks": 7,
        "languages": {"python": 7},
    }


def test_semble_tools_explicitly_declare_read_only_safety() -> None:
    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        fake_index = _FakeIndex()
        adapter = SembleIndexAdapter(workspace_root=workspace_root, index_loader=lambda _root: fake_index)

        search_tool = SemanticSearchTool(adapter)
        related_tool = FindRelatedCodeTool(adapter)

    assert search_tool.read_only_safe is True
    assert related_tool.read_only_safe is True