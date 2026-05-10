"""Typed workspace-intelligence capability models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beep.runtime.capabilities import CapabilityFlag


@dataclass(frozen=True)
class SemanticSearchCapabilities:
    """Semantic-search capabilities exposed to the coding agent."""

    semantic_search: CapabilityFlag
    find_related: CapabilityFlag
    local_indexing: CapabilityFlag
    remote_git_indexing: CapabilityFlag
    hybrid_mode: CapabilityFlag
    semantic_mode: CapabilityFlag
    bm25_mode: CapabilityFlag
    language_filters: CapabilityFlag
    path_filters: CapabilityFlag
    index_stats: CapabilityFlag


@dataclass(frozen=True)
class LSPCapabilities:
    """LSP/editor-operation capabilities exposed to the coding agent."""

    diagnostics: CapabilityFlag
    hover: CapabilityFlag
    definition: CapabilityFlag
    references: CapabilityFlag
    rename: CapabilityFlag
    workspace_symbols: CapabilityFlag
    code_actions: CapabilityFlag
    formatting: CapabilityFlag


@dataclass(frozen=True)
class WorkspaceIntelligenceCapabilities:
    """Combined workspace-intelligence capability set."""

    semantic_search: SemanticSearchCapabilities
    lsp: LSPCapabilities

@dataclass(frozen=True)
class WorkspaceIntelligenceStatusRow:
    """One rendered row inside a workspace-intelligence status section."""

    label: str
    value: str


@dataclass(frozen=True)
class WorkspaceIntelligenceStatusReport:
    """Typed workspace-intelligence status section for CLI rendering."""

    title: str
    rows: tuple[WorkspaceIntelligenceStatusRow, ...]


def _merge_notes(*notes: str) -> str:
    parts: list[str] = []
    for note in notes:
        normalized = str(note or "").strip()
        if normalized and normalized not in parts:
            parts.append(normalized)
    return " | ".join(parts)


def merge_capability_flags(*flags: CapabilityFlag) -> CapabilityFlag:
    """Merge multiple capability flags into one aggregated flag."""
    existing_flags = [flag for flag in flags if isinstance(flag, CapabilityFlag)]
    if not existing_flags:
        return CapabilityFlag(False, "")
    return CapabilityFlag(
        exists=any(flag.exists for flag in existing_flags),
        notes=_merge_notes(*(flag.notes for flag in existing_flags)),
    )


def _merge_section(section_type: type, *sections: object) -> object:
    reference = next((section for section in sections if section is not None), None)
    if reference is None:
        raise ValueError("At least one section is required to merge capability sections.")
    merged_fields = {}
    for name in reference.__dataclass_fields__:
        merged_fields[name] = merge_capability_flags(
            *(getattr(section, name) for section in sections if section is not None)
        )
    return section_type(**merged_fields)


def merge_workspace_intelligence_capabilities(
    base: WorkspaceIntelligenceCapabilities,
    *extras: WorkspaceIntelligenceCapabilities,
) -> WorkspaceIntelligenceCapabilities:
    """Merge built-in and plugin-contributed workspace-intelligence capabilities."""
    all_capabilities = (base, *extras)
    semantic_search = _merge_section(
        SemanticSearchCapabilities,
        *(cap.semantic_search for cap in all_capabilities if cap is not None),
    )
    lsp = _merge_section(
        LSPCapabilities,
        *(cap.lsp for cap in all_capabilities if cap is not None),
    )
    return WorkspaceIntelligenceCapabilities(semantic_search=semantic_search, lsp=lsp)


def build_workspace_intelligence_capabilities(
    semantic_search_report: dict[str, Any] | None,
) -> WorkspaceIntelligenceCapabilities:
    """Build typed workspace-intelligence capabilities from runtime reports."""
    report = semantic_search_report or {}
    available = bool(report.get("available"))
    base_note = str(report.get("error") or "Semble semantic search is unavailable in the current runtime.")

    if available:
        semantic_search = SemanticSearchCapabilities(
            semantic_search=CapabilityFlag(True, "Semble semantic retrieval available."),
            find_related=CapabilityFlag(True, "Semble related-code retrieval available."),
            local_indexing=CapabilityFlag(True, "Indexes the local workspace through SembleIndex.from_path()."),
            remote_git_indexing=CapabilityFlag(
                False,
                "Remote git indexing is supported by Semble but is not exposed by the current internal adapter.",
            ),
            hybrid_mode=CapabilityFlag(True, "Hybrid retrieval mode available."),
            semantic_mode=CapabilityFlag(True, "Semantic-only retrieval mode available."),
            bm25_mode=CapabilityFlag(True, "Lexical BM25 retrieval mode available."),
            language_filters=CapabilityFlag(True, "Language filters are supported."),
            path_filters=CapabilityFlag(True, "Path filters are supported."),
            index_stats=CapabilityFlag(True, "Cached index stats are reported when an index has been built."),
        )
    else:
        semantic_search = SemanticSearchCapabilities(
            semantic_search=CapabilityFlag(False, base_note),
            find_related=CapabilityFlag(False, base_note),
            local_indexing=CapabilityFlag(False, base_note),
            remote_git_indexing=CapabilityFlag(
                False,
                "Remote git indexing is not exposed by the current internal adapter.",
            ),
            hybrid_mode=CapabilityFlag(False, base_note),
            semantic_mode=CapabilityFlag(False, base_note),
            bm25_mode=CapabilityFlag(False, base_note),
            language_filters=CapabilityFlag(False, base_note),
            path_filters=CapabilityFlag(False, base_note),
            index_stats=CapabilityFlag(False, base_note),
        )

    lsp_note = "LSP workspace intelligence is not implemented yet."
    lsp = LSPCapabilities(
        diagnostics=CapabilityFlag(False, lsp_note),
        hover=CapabilityFlag(False, lsp_note),
        definition=CapabilityFlag(False, lsp_note),
        references=CapabilityFlag(False, lsp_note),
        rename=CapabilityFlag(False, lsp_note),
        workspace_symbols=CapabilityFlag(False, lsp_note),
        code_actions=CapabilityFlag(False, lsp_note),
        formatting=CapabilityFlag(False, lsp_note),
    )
    return WorkspaceIntelligenceCapabilities(semantic_search=semantic_search, lsp=lsp)

def build_semantic_search_status_report(
    semantic_search_report: dict[str, Any] | None,
    *,
    title: str = "Workspace Intelligence",
) -> WorkspaceIntelligenceStatusReport:
    """Build a typed status report for Semble-backed workspace intelligence."""
    report = semantic_search_report or {}
    rows: list[WorkspaceIntelligenceStatusRow] = [
        WorkspaceIntelligenceStatusRow(
            "Semble Available",
            "Yes" if report.get("available") else "No",
        ),
        WorkspaceIntelligenceStatusRow(
            "Workspace",
            str(report.get("workspace_root") or "None"),
        ),
        WorkspaceIntelligenceStatusRow(
            "Index Cached",
            "Yes" if report.get("cached") else "No",
        ),
        WorkspaceIntelligenceStatusRow(
            "Cached Root",
            str(report.get("cached_root") or "None"),
        ),
        WorkspaceIntelligenceStatusRow(
            "Last Error",
            str(report.get("error") or "None"),
        ),
    ]

    stats = report.get("stats")
    if isinstance(stats, dict):
        rows.extend(
            [
                WorkspaceIntelligenceStatusRow(
                    "Indexed Files",
                    str(stats.get("indexed_files", 0)),
                ),
                WorkspaceIntelligenceStatusRow(
                    "Total Chunks",
                    str(stats.get("total_chunks", 0)),
                ),
            ]
        )
        languages = stats.get("languages")
        if isinstance(languages, dict) and languages:
            language_summary = ", ".join(
                f"{language}={count}" for language, count in sorted(languages.items())
            )
        else:
            language_summary = "None"
        rows.append(WorkspaceIntelligenceStatusRow("Languages", language_summary))

    return WorkspaceIntelligenceStatusReport(title=title, rows=tuple(rows))