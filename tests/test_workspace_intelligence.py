"""Tests for typed workspace-intelligence capability models."""

from __future__ import annotations

from beep.runtime.capabilities import CapabilityFlag
from beep.runtime.workspace_intelligence import (
    LSPCapabilities,
    SemanticSearchCapabilities,
    WorkspaceIntelligenceCapabilities,
    build_workspace_intelligence_capabilities,
    merge_workspace_intelligence_capabilities,
)


def test_build_workspace_intelligence_capabilities_available_semantic_search() -> None:
    capabilities = build_workspace_intelligence_capabilities(
        {
            "available": True,
            "error": None,
        }
    )

    assert capabilities.semantic_search.semantic_search.exists is True
    assert capabilities.semantic_search.find_related.exists is True
    assert capabilities.semantic_search.remote_git_indexing.exists is False
    assert capabilities.lsp.diagnostics.exists is False


def test_build_workspace_intelligence_capabilities_unavailable_semantic_search() -> None:
    capabilities = build_workspace_intelligence_capabilities(
        {
            "available": False,
            "error": "Semble is not installed.",
        }
    )

    assert capabilities.semantic_search.semantic_search.exists is False
    assert capabilities.semantic_search.semantic_search.notes == "Semble is not installed."
    assert capabilities.semantic_search.hybrid_mode.exists is False
    assert capabilities.lsp.references.exists is False


def test_merge_workspace_intelligence_capabilities_merges_plugin_lsp_support() -> None:
    base = build_workspace_intelligence_capabilities(
        {"available": True, "error": None}
    )
    plugin = WorkspaceIntelligenceCapabilities(
        semantic_search=SemanticSearchCapabilities(
            semantic_search=CapabilityFlag(False, "Plugin does not provide semantic search."),
            find_related=CapabilityFlag(False, "Plugin does not provide related search."),
            local_indexing=CapabilityFlag(False, "Plugin does not index locally."),
            remote_git_indexing=CapabilityFlag(False, "Plugin does not index git remotes."),
            hybrid_mode=CapabilityFlag(False, "Plugin does not provide hybrid search."),
            semantic_mode=CapabilityFlag(False, "Plugin does not provide semantic-only search."),
            bm25_mode=CapabilityFlag(False, "Plugin does not provide BM25 search."),
            language_filters=CapabilityFlag(False, "Plugin does not provide language filters."),
            path_filters=CapabilityFlag(False, "Plugin does not provide path filters."),
            index_stats=CapabilityFlag(False, "Plugin does not provide index stats."),
        ),
        lsp=LSPCapabilities(
            diagnostics=CapabilityFlag(True, "Plugin diagnostics available."),
            hover=CapabilityFlag(True, "Plugin hover available."),
            definition=CapabilityFlag(True, "Plugin definitions available."),
            references=CapabilityFlag(False, "Plugin references unavailable."),
            rename=CapabilityFlag(False, "Plugin rename unavailable."),
            workspace_symbols=CapabilityFlag(False, "Plugin workspace symbols unavailable."),
            code_actions=CapabilityFlag(False, "Plugin code actions unavailable."),
            formatting=CapabilityFlag(False, "Plugin formatting unavailable."),
        ),
    )

    merged = merge_workspace_intelligence_capabilities(base, plugin)

    assert merged.semantic_search.semantic_search.exists is True
    assert merged.lsp.diagnostics.exists is True
    assert "Plugin diagnostics available." in merged.lsp.diagnostics.notes