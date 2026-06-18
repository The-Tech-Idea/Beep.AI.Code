"""Tests for integration governance policies."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.integrations.governance import (
    compute_integrity_checksum,
    is_install_allowed,
    verify_integrity,
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


class TestIsInstallAllowed:
    def test_first_party_always_allowed(self) -> None:
        entry = _make_entry()
        decision = is_install_allowed(entry)
        assert decision.allowed is True

    def test_verified_without_network_allowed(self) -> None:
        entry = _make_entry(trust=TrustTier.verified, requires_network=False)
        decision = is_install_allowed(entry, network_enabled=False)
        assert decision.allowed is True

    def test_external_denied_without_explicit(self) -> None:
        entry = _make_entry(
            id="ext-skill",
            trust=TrustTier.external,
            requires_network=True,
        )
        decision = is_install_allowed(entry)
        assert decision.allowed is False
        assert "external" in decision.reason.lower()

    def test_external_allowed_with_yes(self) -> None:
        entry = _make_entry(
            id="ext-skill",
            trust=TrustTier.external,
            requires_network=True,
        )
        decision = is_install_allowed(entry, allow_external=True, network_enabled=True)
        assert decision.allowed is True

    def test_network_required_denied_without_gate(self) -> None:
        entry = _make_entry(trust=TrustTier.verified, requires_network=True)
        decision = is_install_allowed(entry, network_enabled=False)
        assert decision.allowed is False
        assert "network" in decision.reason.lower()

    def test_network_required_allowed_with_gate(self) -> None:
        entry = _make_entry(trust=TrustTier.verified, requires_network=True)
        decision = is_install_allowed(entry, network_enabled=True)
        assert decision.allowed is True

    def test_external_plus_network(self) -> None:
        entry = _make_entry(
            id="ext",
            trust=TrustTier.external,
            requires_network=True,
        )
        decision = is_install_allowed(entry, allow_external=False, network_enabled=True)
        assert decision.allowed is False
        assert "external" in decision.reason.lower()


class TestVerifyIntegrity:
    def test_same_content_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "test.md"
            file_path.write_text("hello world")
            checksum = compute_integrity_checksum(root)
            assert verify_integrity(root, checksum) is True

    def test_different_content_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "test.md"
            file_path.write_text("hello world")
            checksum = compute_integrity_checksum(root)
            file_path.write_text("goodbye world")
            assert verify_integrity(root, checksum) is False

    def test_missing_path_fails(self) -> None:
        assert verify_integrity(Path("/nonexistent/path"), "abc") is False

    def test_checksum_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("a.md").write_text("content a")
            root.joinpath("b.md").write_text("content b")
            c1 = compute_integrity_checksum(root)
            c2 = compute_integrity_checksum(root)
            assert c1 == c2

    def test_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "single.md"
            f.write_text("hello")
            checksum = compute_integrity_checksum(f)
            assert verify_integrity(f, checksum) is True
