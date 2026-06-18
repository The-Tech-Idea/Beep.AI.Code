"""Tests for integration audit log."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from beep.integrations import audit


@pytest.fixture(autouse=True)
def _isolate_audit_log() -> None:
    yield
    audit._audit_log_path.cache_clear() if hasattr(audit._audit_log_path, "cache_clear") else None


class TestAuditLog:
    def test_record_and_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            integrations_dir = Path(tmp)
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(integrations_dir))

            audit.record("install", "open-design", "success", "with confirmation")
            audit.record("remove", "graphify", "success")

            entries = audit.read_log()
            assert len(entries) == 2
            assert entries[0]["action"] == "install"
            assert entries[0]["entry_id"] == "open-design"
            assert entries[0]["outcome"] == "success"
            assert "timestamp" in entries[0]
            assert entries[1]["action"] == "remove"
            assert entries[1]["entry_id"] == "graphify"

    def test_record_install_includes_metadata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from beep.integrations.models import InstalledRecord, EntryKind

        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))

            rec = InstalledRecord(
                id="graphify",
                kind=EntryKind.skill,
                version="main",
                source_url="https://github.com/safishamsi/graphify",
                checksum="abc123",
                target_path="/tmp/skills/graphify",
            )
            audit.record_install(rec)

            entries = audit.read_log()
            assert len(entries) == 1
            assert entries[0]["action"] == "install"
            assert entries[0]["entry_id"] == "graphify"
            details = json.loads(str(entries[0]["details"]))
            assert details["version"] == "main"
            assert details["checksum"] == "abc123"

    def test_record_remove(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))

            audit.record_remove("code-review")
            entries = audit.read_log()
            assert len(entries) == 1
            assert entries[0]["action"] == "remove"
            assert entries[0]["entry_id"] == "code-review"

    def test_read_log_empty_when_no_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv("BEEP_INTEGRATIONS_DIR", str(Path(tmp)))
            entries = audit.read_log()
            assert entries == []

    def test_default_dir_in_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(Path, "home", lambda: Path(tmp))
            monkeypatch.delenv("BEEP_INTEGRATIONS_DIR", raising=False)

            result_path = audit._audit_log_path()
            expected = Path(tmp) / ".beepai" / "integrations" / "audit.log"
            assert result_path == expected
