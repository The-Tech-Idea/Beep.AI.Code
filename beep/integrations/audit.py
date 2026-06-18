"""Append-only audit log for integration actions."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from beep.integrations.models import InstalledRecord


def _audit_log_path() -> Path:
    base = Path(os.environ.get("BEEP_INTEGRATIONS_DIR", Path.home() / ".beepai" / "integrations"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "audit.log"


def record(action: str, entry_id: str, outcome: str, details: str = "") -> None:
    entry = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "action": action,
        "entry_id": entry_id,
        "outcome": outcome,
        "details": details,
    }
    path = _audit_log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_install(record: InstalledRecord) -> None:
    entry = {
        "timestamp": record.installed_at.isoformat(),
        "action": "install",
        "entry_id": record.id,
        "outcome": "success",
        "details": json.dumps(
            {
                "kind": record.kind.value,
                "version": record.version,
                "source_url": record.source_url,
                "target_path": record.target_path,
                "checksum": record.checksum,
            }
        ),
    }
    path = _audit_log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_remove(entry_id: str) -> None:
    record("remove", entry_id, "success")


def read_log() -> list[dict[str, object]]:
    path = _audit_log_path()
    if not path.exists():
        return []
    entries: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({"raw": line, "error": "invalid JSON"})
    return entries
