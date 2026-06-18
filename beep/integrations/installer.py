"""Integration installer — install, remove, update, and list installed entries."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from beep.integrations.audit import record_install as _audit_install
from beep.integrations.audit import record_remove as _audit_remove
from beep.integrations.governance import (
    compute_integrity_checksum,
    is_install_allowed,
)
from beep.integrations.models import CatalogEntry, EntryKind, InstalledRecord
from beep.integrations.skills_source import materialize_skill


def _installed_path() -> Path:
    base = Path(
        os.environ.get(
            "BEEP_INTEGRATIONS_DIR",
            Path.home() / ".beepai" / "integrations",
        )
    )
    base.mkdir(parents=True, exist_ok=True)
    return base / "installed.json"


def _write_atomic(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    tmp_path.replace(path)


def _load_installed() -> list[dict[str, object]]:
    path = _installed_path()
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _dump_installed(records: list[dict[str, object]]) -> None:
    _write_atomic(_installed_path(), json.dumps(records, indent=2, ensure_ascii=False))


def list_installed() -> list[InstalledRecord]:
    raw = _load_installed()
    result: list[InstalledRecord] = []
    for item in raw:
        installed_at_raw = item.get("installed_at")
        installed_at: datetime | None = None
        if isinstance(installed_at_raw, str):
            installed_at = datetime.fromisoformat(installed_at_raw)
        result.append(
            InstalledRecord(
                id=str(item.get("id", "")),
                kind=EntryKind(str(item.get("kind", "skill"))),
                version=str(item.get("version", "")),
                installed_at=(installed_at or datetime.now(tz=UTC)),
                source_url=str(item.get("source_url", "")),
                checksum=str(item.get("checksum", "")),
                target_path=str(item.get("target_path", "")),
            )
        )
    return result


def is_installed(entry_id: str) -> bool:
    return any(r.id == entry_id for r in list_installed())


def install(
    entry: CatalogEntry,
    *,
    allow_external: bool = False,
    network_enabled: bool = False,
) -> InstalledRecord:
    decision = is_install_allowed(
        entry,
        allow_external=allow_external,
        network_enabled=network_enabled,
    )
    if not decision.allowed:
        raise PermissionError(decision.reason)

    if entry.kind == EntryKind.skill:
        target = materialize_skill(entry)
        checksum = compute_integrity_checksum(target)
        record = InstalledRecord(
            id=entry.id,
            kind=entry.kind,
            version=entry.version,
            source_url=entry.source_url,
            checksum=checksum,
            target_path=str(target),
        )
    elif entry.kind == EntryKind.mcp:
        record = InstalledRecord(
            id=entry.id,
            kind=entry.kind,
            version=entry.version,
            source_url=entry.source_url,
            target_path="",
        )
    else:
        record = InstalledRecord(
            id=entry.id,
            kind=entry.kind,
            version=entry.version,
            source_url=entry.source_url,
            target_path="",
        )

    raw = _load_installed()
    raw = [item for item in raw if item.get("id") != entry.id]
    raw.append(record.model_dump(mode="json"))
    _dump_installed(raw)
    _audit_install(record)
    return record


def remove(entry_id: str) -> None:
    raw = _load_installed()
    existing = [item for item in raw if item.get("id") == entry_id]
    raw = [item for item in raw if item.get("id") != entry_id]
    _dump_installed(raw)

    for item in existing:
        target_path = str(item.get("target_path", ""))
        if target_path and Path(target_path).exists():
            shutil.rmtree(target_path, ignore_errors=True)

    _audit_remove(entry_id)


def update_entry(
    entry_id: str,
    entry: CatalogEntry,
    *,
    allow_external: bool = False,
    network_enabled: bool = False,
) -> InstalledRecord:
    if is_installed(entry_id):
        remove(entry_id)
    return install(entry, allow_external=allow_external, network_enabled=network_enabled)
