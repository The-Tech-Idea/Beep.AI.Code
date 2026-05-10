"""Automatic workspace context injection for normal chat sessions.

Composes Semble retrieval, smart file selection, and explicit user context
(@file mentions, pinned files) under a unified token budget so that normal
``beep chat`` behaves more like a coding assistant without manual file selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from beep.context.builder import build_context as _build_file_context
from beep.context.window import estimate_tokens
from beep.context.smart import SmartContextBuilder
from beep.workspace.detector import find_workspace_root

# Default budget for auto-injected context characters (not tokens).
# Roughly 8000 tokens * 3 chars/token ≈ 24000 chars.
DEFAULT_AUTO_CONTEXT_BUDGET_CHARS = 24000

# Max files to auto-select before reading content.
MAX_AUTO_FILES = 8


@dataclass
class AutoContextResult:
    """Result of automatic context selection."""

    context_text: str
    sources: list[str] = field(default_factory=list)
    truncated: bool = False
    tokens_used: int = 0


class AutoContextBuilder:
    """Builds automatic workspace context for normal chat sessions.

    The builder checks what workspace-intelligence capabilities are available
    and composes context from the best available sources:

    1. Semble semantic retrieval (when available)
    2. Smart file selection (git-modified, keyword-matched, recently accessed)
    3. Workspace summary (fallback for tiny repos or non-code chats)
    """

    def __init__(
        self,
        workspace_root: Path | None = None,
        *,
        semantic_search_adapter: object | None = None,
        budget_chars: int = DEFAULT_AUTO_CONTEXT_BUDGET_CHARS,
    ) -> None:
        self._root = workspace_root or find_workspace_root()
        self._adapter = semantic_search_adapter
        self._budget_chars = budget_chars
        from beep.app_service import get_app_service

        self._smart = get_app_service().smart_context(self._root)

    def build(self, user_query: str) -> AutoContextResult:
        """Build automatic context for the given user query.

        Args:
            user_query: The user's message text (after @file resolution).

        Returns:
            An AutoContextResult with composed context text and source metadata.
        """
        sources: list[str] = []
        parts: list[str] = []
        chars_used = 0

        # 1. Try Semble semantic retrieval first.
        semble_context = self._get_semble_context(user_query)
        if semble_context:
            token_estimate = estimate_tokens(semble_context)
            if chars_used + len(semble_context) <= self._budget_chars:
                parts.append(semble_context)
                chars_used += len(semble_context)
                sources.append("semantic_search")

        # 2. Add smart-selected files if budget remains.
        remaining_budget = self._budget_chars - chars_used
        if remaining_budget > 500:
            file_context = self._get_smart_file_context(user_query, max_chars=remaining_budget)
            if file_context.text:
                parts.append(file_context.text)
                chars_used += len(file_context.text)
                sources.extend(file_context.sources)

        # 3. Fallback: workspace summary if nothing else was selected.
        if not parts and not user_query.strip():
            summary = self._get_workspace_summary()
            if summary:
                parts.append(summary)
                sources.append("workspace_summary")

        context_text = "\n\n".join(parts) if parts else ""
        truncated = chars_used >= self._budget_chars - 100
        return AutoContextResult(
            context_text=context_text,
            sources=sources,
            truncated=truncated,
            tokens_used=estimate_tokens(context_text),
        )

    def _get_semble_context(self, query: str) -> str | None:
        """Retrieve context via Semble semantic search if available."""
        if self._adapter is None:
            return None
        try:
            search = getattr(self._adapter, "search", None)
            if not callable(search):
                return None
            results = search(query, top_k=5)
            if not results:
                return None
            lines = ["## Semantic Code Retrieval"]
            for i, chunk in enumerate(results[:5], 1):
                path = getattr(chunk, "path", None) or getattr(chunk, "file_path", "unknown")
                content = getattr(chunk, "content", getattr(chunk, "text", ""))
                if content:
                    preview = content[:2000]
                    lines.append(f"\n### {i}. {path}\n```\n{preview}\n```")
            return "\n".join(lines)
        except Exception:
            return None

    def _get_smart_file_context(
        self,
        query: str,
        *,
        max_chars: int,
    ) -> _FileContext:
        """Select and read files using smart heuristics."""
        candidates = self._smart.get_relevant_files(query, max_files=MAX_AUTO_FILES)
        if not candidates:
            return _FileContext(text="", sources=[])

        parts: list[str] = []
        sources: list[str] = []
        chars_used = 0

        file_context_str = _build_file_context(candidates, self._root)
        if file_context_str:
            # Truncate file context if it exceeds remaining budget.
            if len(file_context_str) > max_chars:
                file_context_str = file_context_str[:max_chars]
                file_context_str += "\n\n<!-- context truncated -->"
            parts.append(file_context_str)
            for p in candidates:
                try:
                    rel = p.relative_to(self._root)
                    sources.append(str(rel))
                except ValueError:
                    sources.append(p.name)
            chars_used += len(file_context_str)

        return _FileContext(text="\n".join(parts), sources=sources)

    def _get_workspace_summary(self) -> str | None:
        """Return a brief workspace summary."""
        try:
            from beep.context.builder import get_workspace_summary

            return "## Workspace Overview\n\n" + get_workspace_summary(self._root)
        except Exception:
            return None


@dataclass
class _FileContext:
    """Internal helper for file context results."""

    text: str
    sources: list[str]


def build_auto_context(
    user_query: str,
    workspace_root: Path | None = None,
    *,
    semantic_search_adapter: object | None = None,
    budget_chars: int = DEFAULT_AUTO_CONTEXT_BUDGET_CHARS,
) -> AutoContextResult:
    """Convenience function to build automatic context for a chat message.

    Args:
        user_query: The user's message text.
        workspace_root: Workspace root (auto-detected if None).
        semantic_search_adapter: Optional Semble adapter for semantic retrieval.
        budget_chars: Maximum character budget for auto-injected context.

    Returns:
        AutoContextResult with composed context and source metadata.
    """
    from beep.app_service import get_app_service

    builder = get_app_service().auto_context(workspace_root)
    builder._adapter = semantic_search_adapter
    builder._budget_chars = budget_chars
    return builder.build(user_query)
