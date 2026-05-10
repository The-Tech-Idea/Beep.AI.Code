"""Tests for beep.agent.tools.semantic_search_support helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from beep.agent.tools.semantic_search_support import (
    MAX_TOP_K,
    build_availability_report,
    coerce_mode,
    coerce_string_list,
    coerce_top_k,
    execute_find_related,
    execute_semantic_search,
    format_results,
    is_outside_workspace,
    normalize_index_path,
    resolve_chunk,
    resolve_root,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk(file_path: str, start: int, end: int, content: str = "code") -> SimpleNamespace:
    return SimpleNamespace(file_path=file_path, start_line=start, end_line=end, content=content)


def _result(file_path: str, start: int, end: int, content: str = "code", score: float = 0.9) -> SimpleNamespace:
    chunk = _chunk(file_path, start, end, content)
    return SimpleNamespace(chunk=chunk, score=score, source=SimpleNamespace(value="bm25"))


# ---------------------------------------------------------------------------
# coerce_top_k
# ---------------------------------------------------------------------------

def test_coerce_top_k_default() -> None:
    assert coerce_top_k(5) == 5


def test_coerce_top_k_clamps_minimum() -> None:
    assert coerce_top_k(0) == 1
    assert coerce_top_k(-10) == 1


def test_coerce_top_k_clamps_maximum() -> None:
    assert coerce_top_k(MAX_TOP_K + 100) == MAX_TOP_K


def test_coerce_top_k_accepts_string_integer() -> None:
    assert coerce_top_k("3") == 3


def test_coerce_top_k_raises_on_non_numeric() -> None:
    with pytest.raises(ValueError, match="Invalid top_k"):
        coerce_top_k("not-a-number")


# ---------------------------------------------------------------------------
# coerce_mode
# ---------------------------------------------------------------------------

def test_coerce_mode_hybrid() -> None:
    assert coerce_mode("hybrid") == "hybrid"


def test_coerce_mode_semantic() -> None:
    assert coerce_mode("semantic") == "semantic"


def test_coerce_mode_bm25() -> None:
    assert coerce_mode("bm25") == "bm25"


def test_coerce_mode_none_defaults_to_hybrid() -> None:
    assert coerce_mode(None) == "hybrid"


def test_coerce_mode_normalizes_case() -> None:
    assert coerce_mode("HYBRID") == "hybrid"


def test_coerce_mode_raises_on_unknown() -> None:
    with pytest.raises(ValueError, match="Invalid search mode"):
        coerce_mode("fuzzy")


# ---------------------------------------------------------------------------
# coerce_string_list
# ---------------------------------------------------------------------------

def test_coerce_string_list_none_returns_none() -> None:
    assert coerce_string_list(None) is None


def test_coerce_string_list_single_string() -> None:
    assert coerce_string_list("python") == ["python"]


def test_coerce_string_list_list() -> None:
    assert coerce_string_list(["python", "typescript"]) == ["python", "typescript"]


def test_coerce_string_list_strips_whitespace() -> None:
    assert coerce_string_list(["  python  ", " ts "]) == ["python", "ts"]


def test_coerce_string_list_drops_empty() -> None:
    assert coerce_string_list(["python", "  ", ""]) == ["python"]


def test_coerce_string_list_all_empty_returns_none() -> None:
    assert coerce_string_list(["  ", ""]) is None


def test_coerce_string_list_raises_on_non_iterable() -> None:
    with pytest.raises(ValueError, match="string list"):
        coerce_string_list(42)


# ---------------------------------------------------------------------------
# is_outside_workspace
# ---------------------------------------------------------------------------

def test_is_outside_workspace_returns_false_when_no_root() -> None:
    assert is_outside_workspace(workspace_root=None, path=Path("/anywhere")) is False


def test_is_outside_workspace_inside() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        child = root / "src" / "file.py"
        assert is_outside_workspace(workspace_root=root, path=child) is False


def test_is_outside_workspace_outside() -> None:
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        root = Path(td1)
        outside = Path(td2) / "other.py"
        assert is_outside_workspace(workspace_root=root, path=outside) is True


def test_is_outside_workspace_equal_to_root() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        assert is_outside_workspace(workspace_root=root, path=root) is False


# ---------------------------------------------------------------------------
# resolve_root
# ---------------------------------------------------------------------------

def test_resolve_root_uses_workspace_when_path_is_none() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        resolved = resolve_root(None, workspace_root=root)
        assert resolved == root


def test_resolve_root_accepts_explicit_path() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        resolved = resolve_root(str(root), workspace_root=root)
        assert resolved == root


def test_resolve_root_raises_on_nonexistent_path() -> None:
    with pytest.raises(FileNotFoundError):
        resolve_root("/nonexistent/path/abc123", workspace_root=None)


def test_resolve_root_raises_on_file_not_directory() -> None:
    with tempfile.NamedTemporaryFile() as f:
        with pytest.raises(NotADirectoryError):
            resolve_root(f.name, workspace_root=None)


def test_resolve_root_raises_outside_workspace() -> None:
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        with pytest.raises(ValueError, match="outside workspace"):
            resolve_root(td2, workspace_root=Path(td1))


# ---------------------------------------------------------------------------
# normalize_index_path
# ---------------------------------------------------------------------------

def test_normalize_index_path_relative_stays_relative() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        result = normalize_index_path("src/file.py", root=root, workspace_root=root)
        assert result == "src/file.py"


def test_normalize_index_path_backslash_converted() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        result = normalize_index_path("src\\file.py", root=root, workspace_root=root)
        assert result == "src/file.py"


def test_normalize_index_path_absolute_inside_workspace() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        child = root / "a" / "b.py"
        child.parent.mkdir(parents=True, exist_ok=True)
        child.touch()
        result = normalize_index_path(str(child), root=root, workspace_root=root)
        assert result == "a/b.py"


def test_normalize_index_path_absolute_outside_workspace_raises() -> None:
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        root = Path(td1).resolve()
        outside = Path(td2).resolve() / "bad.py"
        with pytest.raises(ValueError, match="outside workspace"):
            normalize_index_path(str(outside), root=root, workspace_root=root)


# ---------------------------------------------------------------------------
# resolve_chunk
# ---------------------------------------------------------------------------

def test_resolve_chunk_finds_exact_match() -> None:
    chunks = [
        _chunk("src/a.py", 1, 10),
        _chunk("src/a.py", 11, 20),
    ]
    result = resolve_chunk(chunks, file_path="src/a.py", line=5)
    assert result is chunks[0]


def test_resolve_chunk_returns_none_for_wrong_file() -> None:
    chunks = [_chunk("src/a.py", 1, 10)]
    result = resolve_chunk(chunks, file_path="src/b.py", line=5)
    assert result is None


def test_resolve_chunk_falls_back_to_chunk_ending_at_line() -> None:
    chunks = [_chunk("src/a.py", 1, 5)]
    result = resolve_chunk(chunks, file_path="src/a.py", line=5)
    assert result is chunks[0]


def test_resolve_chunk_returns_none_for_out_of_range() -> None:
    chunks = [_chunk("src/a.py", 1, 5)]
    result = resolve_chunk(chunks, file_path="src/a.py", line=99)
    assert result is None


# ---------------------------------------------------------------------------
# build_availability_report
# ---------------------------------------------------------------------------

def test_availability_report_unavailable_when_semble_missing() -> None:
    def _failing_loader() -> type:
        raise RuntimeError("Semble is not installed.")

    report = build_availability_report(
        workspace_root=None,
        cached_root=None,
        cached_index=None,
        load_semble_index=_failing_loader,
    )
    assert report["available"] is False
    assert "Semble is not installed" in report["error"]


def test_availability_report_available_no_cache() -> None:
    def _ok_loader() -> type:
        return object

    report = build_availability_report(
        workspace_root=None,
        cached_root=None,
        cached_index=None,
        load_semble_index=_ok_loader,
    )
    assert report["available"] is True
    assert report["cached"] is False
    assert report["stats"] is None


def test_availability_report_includes_stats_when_cached() -> None:
    def _ok_loader() -> type:
        return object

    stats = SimpleNamespace(indexed_files=10, total_chunks=50, languages={"python": 10})
    fake_index = SimpleNamespace(stats=stats)
    root = Path("/workspace")

    report = build_availability_report(
        workspace_root=root,
        cached_root=root,
        cached_index=fake_index,
        load_semble_index=_ok_loader,
    )
    assert report["available"] is True
    assert report["cached"] is True
    assert report["stats"]["indexed_files"] == 10
    assert report["stats"]["total_chunks"] == 50
    assert report["stats"]["languages"] == {"python": 10}


# ---------------------------------------------------------------------------
# format_results
# ---------------------------------------------------------------------------

def test_format_results_single_result() -> None:
    results = [_result("src/a.py", 1, 10, content="def foo(): pass")]
    output = format_results("Results for: 'foo'", results)
    assert "src/a.py:1-10" in output
    assert "def foo(): pass" in output
    assert "score=0.900" in output


def test_format_results_skips_results_without_chunk() -> None:
    results = [SimpleNamespace(chunk=None, score=0.5, source=None)]
    output = format_results("header", results)
    assert "header" in output
    assert "score" not in output


def test_format_results_empty_list() -> None:
    output = format_results("Empty header", [])
    assert output == "Empty header"


# ---------------------------------------------------------------------------
# execute_semantic_search
# ---------------------------------------------------------------------------

def _make_search_adapter(results: list[Any]) -> Any:
    def search(**_kwargs: Any) -> list[Any]:
        return results

    return SimpleNamespace(search=search)


def test_execute_semantic_search_returns_results() -> None:
    results = [_result("src/a.py", 1, 10, content="import os")]
    adapter = _make_search_adapter(results)
    tool_result = execute_semantic_search(adapter=adapter, query="os import")
    assert tool_result.success is True
    assert "src/a.py" in tool_result.output


def test_execute_semantic_search_empty_query_fails() -> None:
    adapter = _make_search_adapter([])
    tool_result = execute_semantic_search(adapter=adapter, query="   ")
    assert tool_result.success is False
    assert "empty" in tool_result.error.lower()


def test_execute_semantic_search_no_results() -> None:
    adapter = _make_search_adapter([])
    tool_result = execute_semantic_search(adapter=adapter, query="something")
    assert tool_result.success is True
    assert "No results" in tool_result.output


def test_execute_semantic_search_propagates_runtime_error() -> None:
    def bad_search(**_kwargs: Any) -> list[Any]:
        raise RuntimeError("Semble not installed")

    adapter = SimpleNamespace(search=bad_search)
    tool_result = execute_semantic_search(adapter=adapter, query="foo")
    assert tool_result.success is False
    assert "Semble not installed" in tool_result.error


def test_execute_semantic_search_uses_default_mode() -> None:
    captured: dict[str, Any] = {}

    def capturing_search(**kwargs: Any) -> list[Any]:
        captured.update(kwargs)
        return []

    adapter = SimpleNamespace(search=capturing_search)
    execute_semantic_search(adapter=adapter, query="test")
    assert captured.get("mode") == "hybrid"


def test_execute_semantic_search_rejects_invalid_mode() -> None:
    adapter = _make_search_adapter([])
    tool_result = execute_semantic_search(adapter=adapter, query="test", mode="telepathic")
    assert tool_result.success is False
    assert "Invalid search mode" in tool_result.error


# ---------------------------------------------------------------------------
# execute_find_related
# ---------------------------------------------------------------------------

def _make_related_adapter(results: list[Any]) -> Any:
    def find_related(**_kwargs: Any) -> list[Any]:
        return results

    return SimpleNamespace(find_related=find_related)


def test_execute_find_related_returns_results() -> None:
    results = [_result("src/b.py", 5, 15, content="class Foo: pass")]
    adapter = _make_related_adapter(results)
    tool_result = execute_find_related(adapter=adapter, file_path="src/a.py", line=1)
    assert tool_result.success is True
    assert "src/b.py" in tool_result.output


def test_execute_find_related_empty_file_path_fails() -> None:
    adapter = _make_related_adapter([])
    tool_result = execute_find_related(adapter=adapter, file_path="  ", line=1)
    assert tool_result.success is False
    assert "file_path" in tool_result.error


def test_execute_find_related_invalid_line_fails() -> None:
    adapter = _make_related_adapter([])
    tool_result = execute_find_related(adapter=adapter, file_path="src/a.py", line="bad")
    assert tool_result.success is False
    assert "Invalid line" in tool_result.error


def test_execute_find_related_line_less_than_one_fails() -> None:
    adapter = _make_related_adapter([])
    tool_result = execute_find_related(adapter=adapter, file_path="src/a.py", line=0)
    assert tool_result.success is False
    assert ">= 1" in tool_result.error


def test_execute_find_related_no_results() -> None:
    adapter = _make_related_adapter([])
    tool_result = execute_find_related(adapter=adapter, file_path="src/a.py", line=5)
    assert tool_result.success is True
    assert "No related chunks" in tool_result.output


def test_execute_find_related_propagates_value_error() -> None:
    def bad_find(**_kwargs: Any) -> list[Any]:
        raise ValueError("No chunk at that location")

    adapter = SimpleNamespace(find_related=bad_find)
    tool_result = execute_find_related(adapter=adapter, file_path="src/a.py", line=1)
    assert tool_result.success is False
    assert "No chunk" in tool_result.error
