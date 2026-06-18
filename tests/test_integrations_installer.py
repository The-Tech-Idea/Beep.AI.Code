"""Tests for integration installer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from beep.integrations.installer import (
    _installed_path,
    _load_installed,
    _dump_installed,
    list_installed,
    install,
    remove,
    update_entry,
    is_installed,
)
from beep.integrations.models import CatalogEntry, EntryKind, TrustTier


def _make_entry(**kwargs: object) -> CatalogEntry:
    defaults: dict[str, object] = {
        "id": "test-skill",
        "kind": EntryKind.skill,
        "name": "Test Skill",
        "trust": TrustTier.first_party,
    }
    defaults.update(kwargs)
    return CatalogEntry(**defaults)  # type: ignore[arg-type]


class TestInstalledPersistence:
    def test_load_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            assert _load_installed() == []

    def test_dump_and_load(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            records = [{"id": "skill-a", "kind": "skill"}]
            _dump_installed(records)
            loaded = _load_installed()
            assert loaded == records

    def test_atomic_write_does_not_leave_tmp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            _dump_installed([{"id": "x"}])
            path = _installed_path()
            assert path.exists()
            assert not path.with_suffix(".tmp").exists()


class TestInstallRemove:
    def test_install_first_party_skill(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entry = _make_entry(id="code-review", kind=EntryKind.skill)
            record = install(entry)
            assert record.id == "code-review"
            assert is_installed("code-review")

    def test_install_external_denied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entry = _make_entry(
                id="ext-skill",
                trust=TrustTier.external,
                requires_network=True,
            )
            with pytest.raises(PermissionError, match="external"):
                install(entry)

    def test_install_external_allowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entry = _make_entry(
                id="ext-skill",
                trust=TrustTier.external,
                requires_network=True,
            )
            record = install(entry, allow_external=True, network_enabled=True)
            assert record.id == "ext-skill"

    def test_remove_clears_record(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entry = _make_entry(id="test")
            install(entry)
            assert is_installed("test")
            remove("test")
            assert not is_installed("test")

    def test_remove_nonexistent_no_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            remove("nonexistent")

    def test_update_reinstalls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entry = _make_entry(id="test", version="1.0")
            install(entry)
            entry_v2 = _make_entry(id="test", version="2.0")
            update_entry("test", entry_v2)
            records = list_installed()
            assert records[0].version == "2.0"
            assert len(records) == 1

    def test_install_overwrites_previous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            install(_make_entry(id="test"))
            install(_make_entry(id="test", version="v2"))
            records = list_installed()
            assert len(records) == 1
            assert records[0].version == "v2"

    def test_install_mcp_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entry = _make_entry(
                id="github-mcp",
                kind=EntryKind.mcp,
                trust=TrustTier.verified,
            )
            record = install(entry)
            assert record.kind == EntryKind.mcp
            assert is_installed("github-mcp")

    def test_install_tool_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entry = _make_entry(
                id="ripgrep",
                kind=EntryKind.tool,
                trust=TrustTier.verified,
            )
            record = install(entry)
            assert record.kind == EntryKind.tool
            assert is_installed("ripgrep")
