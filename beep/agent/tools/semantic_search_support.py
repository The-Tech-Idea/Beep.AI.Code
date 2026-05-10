"""Support helpers for Semble-backed semantic search tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import ToolResult

DEFAULT_TOP_K = 5
MAX_TOP_K = 20
VALID_MODES = frozenset({"hybrid", "semantic", "bm25"})


def format_results(header: str, results: list[Any]) -> str:
    sections = [header]
    for index, result in enumerate(results, start=1):
        chunk = getattr(result, "chunk", None)
        if chunk is None:
            continue
        score = getattr(result, "score", None)
        source = getattr(result, "source", None)
        source_value = getattr(source, "value", source)
        meta: list[str] = []
        if isinstance(score, int | float):
            meta.append(f"score={score:.3f}")
        if source_value:
            meta.append(f"source={source_value}")
        location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
        if meta:
            location = f"{location} ({', '.join(meta)})"
        sections.append(f"{index}. {location}")
        sections.append("```")
        sections.append(str(getattr(chunk, "content", "")).rstrip())
        sections.append("```")
    return "\n".join(sections)


def coerce_top_k(value: Any) -> int:
    try:
        top_k = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid top_k value: {value!r}") from exc
    return min(max(top_k, 1), MAX_TOP_K)


def coerce_mode(value: Any) -> str:
    mode = str(value or "hybrid").strip().lower()
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid search mode: {mode!r}. Expected one of: {', '.join(sorted(VALID_MODES))}.")
    return mode


def coerce_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list | tuple | set):
        values = list(value)
    else:
        raise ValueError(f"Expected a string list, got {type(value).__name__}.")

    normalized = [str(item).strip() for item in values if str(item).strip()]
    return normalized or None


def is_outside_workspace(*, workspace_root: Path | None, path: Path) -> bool:
    return bool(
        workspace_root
        and workspace_root not in path.parents
        and path != workspace_root
    )


def resolve_root(raw_path: str | None, *, workspace_root: Path | None) -> Path:
    root_str = raw_path or (str(workspace_root) if workspace_root else ".")
    root = Path(root_str).resolve()
    if is_outside_workspace(workspace_root=workspace_root, path=root):
        raise ValueError(f"Path outside workspace: {raw_path}")
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root_str}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_str}")
    return root


def build_availability_report(
    *,
    workspace_root: Path | None,
    cached_root: Path | None,
    cached_index: Any,
    load_semble_index: Any,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "available": False,
        "workspace_root": str(workspace_root) if workspace_root else None,
        "cached": cached_root is not None and cached_index is not None,
        "cached_root": str(cached_root) if cached_root else None,
        "stats": None,
        "error": None,
    }
    try:
        load_semble_index()
    except RuntimeError as exc:
        report["error"] = str(exc)
        return report

    report["available"] = True
    if cached_index is None:
        return report

    try:
        stats = getattr(cached_index, "stats", None)
        if stats is None:
            return report
        languages = getattr(stats, "languages", {}) or {}
        report["stats"] = {
            "indexed_files": int(getattr(stats, "indexed_files", 0) or 0),
            "total_chunks": int(getattr(stats, "total_chunks", 0) or 0),
            "languages": dict(languages),
        }
    except Exception as exc:
        report["error"] = str(exc)
    return report


def normalize_index_path(raw_path: str, *, root: Path, workspace_root: Path | None) -> str:
    path = Path(raw_path)
    if path.is_absolute():
        resolved = path.resolve()
        if is_outside_workspace(workspace_root=workspace_root, path=resolved) or (
            root not in resolved.parents and resolved != root
        ):
            raise ValueError(f"Path outside workspace: {raw_path}")
        return resolved.relative_to(root).as_posix()
    return str(path).replace("\\", "/")


def resolve_chunk(chunks: list[Any], *, file_path: str, line: int) -> Any | None:
    fallback = None
    for chunk in chunks:
        if chunk.file_path != file_path:
            continue
        if chunk.start_line <= line <= chunk.end_line:
            if line < chunk.end_line:
                return chunk
            if fallback is None:
                fallback = chunk
    return fallback


def execute_semantic_search(
    *,
    adapter: Any,
    query: Any,
    path: Any = None,
    top_k: Any = None,
    mode: Any = None,
    filter_languages: Any = None,
    filter_paths: Any = None,
) -> ToolResult:
    query_text = str("" if query is None else query).strip()
    if not query_text:
        return ToolResult(success=False, output="", error="Query cannot be empty.")
    try:
        normalized_top_k = coerce_top_k(DEFAULT_TOP_K if top_k is None else top_k)
        normalized_mode = coerce_mode("hybrid" if mode is None else mode)
        normalized_languages = coerce_string_list(filter_languages)
        normalized_paths = coerce_string_list(filter_paths)
        results = adapter.search(
            query=query_text,
            path=path,
            top_k=normalized_top_k,
            mode=normalized_mode,
            filter_languages=normalized_languages,
            filter_paths=normalized_paths,
        )
    except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError) as exc:
        return ToolResult(success=False, output="", error=str(exc))

    if not results:
        return ToolResult(success=True, output="No results found.")

    return ToolResult(
        success=True,
        output=format_results(f"Search results for: {query_text!r} (mode={normalized_mode})", results),
    )


def execute_find_related(
    *,
    adapter: Any,
    file_path: Any,
    line: Any,
    path: Any = None,
    top_k: Any = None,
) -> ToolResult:
    normalized_file_path = str("" if file_path is None else file_path).strip()
    if not normalized_file_path:
        return ToolResult(success=False, output="", error="file_path cannot be empty.")
    try:
        normalized_line = int(0 if line is None else line)
    except (TypeError, ValueError):
        return ToolResult(success=False, output="", error=f"Invalid line value: {line!r}")
    if normalized_line < 1:
        return ToolResult(success=False, output="", error="line must be >= 1.")

    try:
        normalized_top_k = coerce_top_k(DEFAULT_TOP_K if top_k is None else top_k)
        results = adapter.find_related(
            file_path=normalized_file_path,
            line=normalized_line,
            path=path,
            top_k=normalized_top_k,
        )
    except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError) as exc:
        return ToolResult(success=False, output="", error=str(exc))

    if not results:
        return ToolResult(success=True, output=f"No related chunks found for {normalized_file_path}:{normalized_line}.")

    return ToolResult(
        success=True,
        output=format_results(f"Chunks related to {normalized_file_path}:{normalized_line}", results),
    )