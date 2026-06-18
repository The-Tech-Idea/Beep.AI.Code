"""Tests for integration catalog models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from beep.integrations.models import CatalogEntry, EntryKind, InstalledRecord, TrustTier


class TestTrustTier:
    def test_values(self) -> None:
        assert TrustTier.first_party == "first_party"
        assert TrustTier.verified == "verified"
        assert TrustTier.external == "external"

    def test_enum_coercion(self) -> None:
        assert TrustTier("first_party") == TrustTier.first_party
        assert TrustTier("verified") == TrustTier.verified
        assert TrustTier("external") == TrustTier.external

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            TrustTier("unknown")


class TestEntryKind:
    def test_values(self) -> None:
        assert EntryKind.skill == "skill"
        assert EntryKind.mcp == "mcp"
        assert EntryKind.tool == "tool"

    def test_enum_coercion(self) -> None:
        assert EntryKind("skill") == EntryKind.skill
        assert EntryKind("mcp") == EntryKind.mcp
        assert EntryKind("tool") == EntryKind.tool


class TestCatalogEntry:
    def test_minimal_creation(self) -> None:
        entry = CatalogEntry(
            id="test",
            kind=EntryKind.skill,
            name="Test",
            summary="A test skill",
            trust=TrustTier.first_party,
        )
        assert entry.id == "test"
        assert entry.kind == EntryKind.skill
        assert entry.trust == TrustTier.first_party
        assert entry.tags == []
        assert not entry.requires_network

    def test_full_creation(self) -> None:
        entry = CatalogEntry(
            id="ext-skill",
            kind=EntryKind.skill,
            name="External Skill",
            summary="An external skill",
            source_url="https://github.com/example/repo",
            version="1.2.3",
            trust=TrustTier.external,
            requires_network=True,
            install_hint="pip install ext-skill",
            tags=["external", "test"],
        )
        assert entry.version == "1.2.3"
        assert entry.source_url == "https://github.com/example/repo"
        assert entry.requires_network is True
        assert entry.install_hint == "pip install ext-skill"
        assert entry.tags == ["external", "test"]

    def test_defaults(self) -> None:
        entry = CatalogEntry(
            id="min",
            kind=EntryKind.tool,
            name="Minimal",
            trust=TrustTier.verified,
        )
        assert entry.summary == ""
        assert entry.source_url == ""
        assert entry.version == ""
        assert entry.requires_network is False
        assert entry.install_hint == ""


class TestInstalledRecord:
    def test_minimal_creation(self) -> None:
        record = InstalledRecord(id="my-skill")
        assert record.id == "my-skill"
        assert record.kind == EntryKind.skill
        assert record.version == ""
        assert record.checksum == ""
        assert record.target_path == ""
        assert isinstance(record.installed_at, datetime)

    def test_installed_at_default_is_utc(self) -> None:
        record = InstalledRecord(id="skill")
        assert record.installed_at.tzinfo == timezone.utc

    def test_full_creation(self) -> None:
        now = datetime(2025, 1, 1, tzinfo=timezone.utc)
        record = InstalledRecord(
            id="graphify",
            kind=EntryKind.skill,
            version="main",
            installed_at=now,
            source_url="https://github.com/safishamsi/graphify",
            checksum="abc123",
            target_path="/home/user/.beepai/skills/graphify",
        )
        assert record.kind == EntryKind.skill
        assert record.version == "main"
        assert record.source_url == "https://github.com/safishamsi/graphify"
        assert record.checksum == "abc123"
        assert record.target_path == "/home/user/.beepai/skills/graphify"
