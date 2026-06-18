"""Integrations registry — thin facade wrapping catalog, installer, and audit."""

from __future__ import annotations

from beep.integrations.catalog import CURATED_ENTRIES, find, search
from beep.integrations.installer import install, is_installed, list_installed, remove, update_entry
from beep.integrations.models import CatalogEntry, EntryKind, InstalledRecord


class IntegrationsRegistry:
    """Singleton wrapper for the integrations subsystem."""

    @property
    def curated_entries(self) -> tuple[CatalogEntry, ...]:
        return CURATED_ENTRIES

    def find(self, entry_id: str) -> CatalogEntry | None:
        return find(entry_id)

    def search(self, query: str, kind: EntryKind | None = None) -> list[CatalogEntry]:
        return search(query, kind)

    def install(
        self,
        entry: CatalogEntry,
        *,
        allow_external: bool = False,
        network_enabled: bool = False,
    ) -> InstalledRecord:
        return install(entry, allow_external=allow_external, network_enabled=network_enabled)

    def remove(self, entry_id: str) -> None:
        remove(entry_id)

    def update(
        self,
        entry_id: str,
        entry: CatalogEntry,
        *,
        allow_external: bool = False,
        network_enabled: bool = False,
    ) -> InstalledRecord:
        return update_entry(
            entry_id, entry, allow_external=allow_external, network_enabled=network_enabled
        )

    def list_installed(self) -> list[InstalledRecord]:
        return list_installed()

    def is_installed(self, entry_id: str) -> bool:
        return is_installed(entry_id)
