"""Integration governance — trust tiers, version pins, integrity checks, and network gates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from beep.integrations.models import CatalogEntry, TrustTier


@dataclass
class Decision:
    allowed: bool
    reason: str


def is_install_allowed(
    entry: CatalogEntry,
    *,
    allow_external: bool = False,
    network_enabled: bool = False,
) -> Decision:
    if entry.trust == TrustTier.external and not allow_external:
        return Decision(
            allowed=False,
            reason=f"'{entry.id}' has trust tier 'external'. Use --yes to confirm installation.",
        )
    if entry.requires_network and not network_enabled:
        return Decision(
            allowed=False,
            reason=(
                f"'{entry.id}' requires network access. "
                "Set BEEP_INTEGRATIONS=1 or use --allow-network to proceed."
            ),
        )
    return Decision(allowed=True, reason="OK")


def verify_integrity(path: Path, expected_checksum: str) -> bool:
    if not path.exists():
        return False
    actual = _hash_tree(path)
    return actual == expected_checksum


def compute_integrity_checksum(path: Path) -> str:
    return _hash_tree(path)


def _hash_file(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _hash_tree(root: Path) -> str:
    if root.is_file():
        return _hash_file(root)
    hasher = hashlib.sha256()
    for file_path in sorted(root.rglob("*")):
        if file_path.is_file():
            rel = file_path.relative_to(root).as_posix()
            hasher.update(rel.encode())
            hasher.update(_hash_file(file_path).encode())
    return hasher.hexdigest()
