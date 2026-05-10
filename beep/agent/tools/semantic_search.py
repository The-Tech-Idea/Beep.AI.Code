"""Semble-backed semantic code search tools for the autonomous agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from beep.agent.tools.base import BaseTool, ToolResult
from beep.agent.tools.semantic_search_support import (
    build_availability_report as _build_availability_report,
)
from beep.agent.tools.semantic_search_support import execute_find_related as _execute_find_related
from beep.agent.tools.semantic_search_support import (
    execute_semantic_search as _execute_semantic_search,
)
from beep.agent.tools.semantic_search_support import (
    is_outside_workspace as _is_outside_workspace_impl,
)
from beep.agent.tools.semantic_search_support import (
    normalize_index_path as _normalize_index_path_impl,
)
from beep.agent.tools.semantic_search_support import resolve_chunk as _resolve_chunk_impl
from beep.agent.tools.semantic_search_support import resolve_root as _resolve_root_impl


def _load_semble_index() -> type:
    try:
        from semble import SembleIndex
    except ImportError as exc:
        raise RuntimeError(
            'Semble is not installed in the agent environment. Run "beep agent setup" to install semantic search support.'
        ) from exc
    return SembleIndex


class SembleIndexAdapter:
    """Lazy Semble index loader with per-run caching."""

    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        index_loader: Callable[[Path], Any] | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve() if workspace_root else None
        self._index_loader = index_loader or self._build_index
        self._cached_root: Path | None = None
        self._cached_index: Any = None

    def _is_outside_workspace(self, path: Path) -> bool:
        return _is_outside_workspace_impl(workspace_root=self._workspace_root, path=path)

    def _resolve_root(self, raw_path: str | None) -> Path:
        return _resolve_root_impl(raw_path, workspace_root=self._workspace_root)

    def _build_index(self, root: Path) -> Any:
        return _load_semble_index().from_path(root)

    def _get_index(self, root: Path) -> Any:
        if self._cached_root == root and self._cached_index is not None:
            return self._cached_index
        self._cached_root = root
        self._cached_index = self._index_loader(root)
        return self._cached_index

    def availability_report(self) -> dict[str, Any]:
        """Return runtime availability and cache details for Semble search."""
        return _build_availability_report(
            workspace_root=self._workspace_root,
            cached_root=self._cached_root,
            cached_index=self._cached_index,
            load_semble_index=_load_semble_index,
        )

    def _normalize_index_path(self, raw_path: str, *, root: Path) -> str:
        return _normalize_index_path_impl(
            raw_path,
            root=root,
            workspace_root=self._workspace_root,
        )

    def _resolve_chunk(self, chunks: list[Any], *, file_path: str, line: int) -> Any | None:
        return _resolve_chunk_impl(chunks, file_path=file_path, line=line)

    def search(
        self,
        *,
        query: str,
        path: str | None,
        top_k: int,
        mode: str,
        filter_languages: list[str] | None,
        filter_paths: list[str] | None,
    ) -> list[Any]:
        root = self._resolve_root(path)
        index = self._get_index(root)
        normalized_paths = None
        if filter_paths:
            normalized_paths = [
                self._normalize_index_path(item, root=root) for item in filter_paths
            ]
        return index.search(
            query,
            top_k=top_k,
            mode=mode,
            filter_languages=filter_languages,
            filter_paths=normalized_paths,
        )

    def find_related(
        self,
        *,
        file_path: str,
        line: int,
        path: str | None,
        top_k: int,
    ) -> list[Any]:
        root = self._resolve_root(path)
        index = self._get_index(root)
        normalized_file_path = self._normalize_index_path(file_path, root=root)
        chunk = self._resolve_chunk(index.chunks, file_path=normalized_file_path, line=line)
        if chunk is None:
            raise ValueError(
                f"No chunk found at {normalized_file_path}:{line}. Make sure the file is indexed and the line number is within a known chunk."
            )
        return index.find_related(chunk, top_k=top_k)


class SemanticSearchTool(BaseTool):
    """Search the workspace with Semble's semantic and hybrid retrieval."""

    def __init__(self, adapter: SembleIndexAdapter) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "semantic_search"

    @property
    def description(self) -> str:
        return (
            "Search the workspace with Semble using hybrid, semantic, or BM25 retrieval. "
            "Use this before broad file reads for exploratory code discovery."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "Natural-language or code query to search for.",
            },
            "path": {
                "type": "string",
                "description": "Directory to index (defaults to workspace root).",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of results to return (1-20, default 5).",
            },
            "mode": {
                "type": "string",
                "description": "Search mode: hybrid (default), semantic, or bm25.",
            },
            "filter_languages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional language filters such as ['python', 'typescript'].",
            },
            "filter_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional workspace-relative file paths to restrict retrieval to.",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["path", "top_k", "mode", "filter_languages", "filter_paths"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        return _execute_semantic_search(
            adapter=self._adapter,
            query=kwargs.get("query"),
            path=kwargs.get("path"),
            top_k=kwargs.get("top_k"),
            mode=kwargs.get("mode"),
            filter_languages=kwargs.get("filter_languages"),
            filter_paths=kwargs.get("filter_paths"),
        )


class FindRelatedCodeTool(BaseTool):
    """Find Semble-related code chunks from a known file and line."""

    def __init__(self, adapter: SembleIndexAdapter) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "find_related_code"

    @property
    def description(self) -> str:
        return (
            "Find code chunks semantically similar to a known file and line using Semble. "
            "Use this after semantic_search to explore related implementations."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Workspace-relative or absolute path to a file returned by semantic_search.",
            },
            "line": {
                "type": "integer",
                "description": "1-based line number inside the target file.",
            },
            "path": {
                "type": "string",
                "description": "Directory to index (defaults to workspace root).",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of related chunks to return (1-20, default 5).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["path", "top_k"]

    @property
    def category(self) -> str:
        return "search"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        return _execute_find_related(
            adapter=self._adapter,
            file_path=kwargs.get("file_path"),
            line=kwargs.get("line"),
            path=kwargs.get("path"),
            top_k=kwargs.get("top_k"),
        )


def build_semble_tools(
    *,
    workspace_root: Path | None = None,
    adapter: SembleIndexAdapter | None = None,
) -> tuple[BaseTool, BaseTool]:
    """Build Semble-backed tools that share one cached workspace index."""
    if adapter is None:
        from beep.app_service import get_app_service

        shared_adapter = get_app_service().semble_index(workspace_root)
    else:
        shared_adapter = adapter
    return SemanticSearchTool(shared_adapter), FindRelatedCodeTool(shared_adapter)
