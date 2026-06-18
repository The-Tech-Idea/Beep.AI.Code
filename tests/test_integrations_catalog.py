"""Tests for integration catalog lookup and search."""

from __future__ import annotations

import pytest

from beep.integrations.catalog import CURATED_ENTRIES, find, search
from beep.integrations.models import EntryKind, TrustTier


class TestCatalogIntegrity:
    def test_no_duplicate_ids(self) -> None:
        ids = [entry.id for entry in CURATED_ENTRIES]
        assert len(ids) == len(set(ids))

    def test_external_entries_require_network(self) -> None:
        for entry in CURATED_ENTRIES:
            if entry.trust == TrustTier.external:
                assert entry.requires_network, (
                    f"External entry '{entry.id}' must set requires_network=True"
                )

    def test_all_have_kind(self) -> None:
        for entry in CURATED_ENTRIES:
            assert entry.kind in (EntryKind.skill, EntryKind.mcp, EntryKind.tool)

    def test_skill_count(self) -> None:
        skills = [e for e in CURATED_ENTRIES if e.kind == EntryKind.skill]
        assert len(skills) >= 4


class TestFind:
    def test_find_existing(self) -> None:
        entry = find("open-design")
        assert entry is not None
        assert entry.id == "open-design"
        assert entry.trust == TrustTier.external

    def test_find_first_party(self) -> None:
        entry = find("code-review")
        assert entry is not None
        assert entry.trust == TrustTier.first_party

    def test_find_tool(self) -> None:
        entry = find("ripgrep")
        assert entry is not None
        assert entry.kind == EntryKind.tool

    def test_find_mcp(self) -> None:
        entry = find("github-mcp")
        assert entry is not None
        assert entry.kind == EntryKind.mcp

    def test_find_missing(self) -> None:
        assert find("nonexistent") is None


class TestSearch:
    def test_search_by_id(self) -> None:
        results = search("graphify")
        assert len(results) == 1
        assert results[0].id == "graphify"

    def test_search_by_name(self) -> None:
        results = search("ripgrep")
        assert len(results) >= 1
        assert any(r.id == "ripgrep" for r in results)

    def test_search_by_summary(self) -> None:
        results = search("knowledge graph")
        assert len(results) >= 1
        assert results[0].id == "graphify"

    def test_search_by_tag(self) -> None:
        results = search("python")
        python_ids = {r.id for r in results}
        assert "ruff" in python_ids

    def test_search_kind_filter(self) -> None:
        results = search("review", kind=EntryKind.skill)
        assert len(results) >= 1
        for r in results:
            assert r.kind == EntryKind.skill

    def test_search_case_insensitive(self) -> None:
        results_lower = search("ripgrep")
        results_upper = search("RIPGREP")
        assert len(results_lower) == len(results_upper)

    def test_search_no_match(self) -> None:
        results = search("zzzzzznothing")
        assert results == []
