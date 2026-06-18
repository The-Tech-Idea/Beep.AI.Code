"""Integration catalog data models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TrustTier(StrEnum):
    first_party = "first_party"
    verified = "verified"
    external = "external"


class EntryKind(StrEnum):
    skill = "skill"
    mcp = "mcp"
    tool = "tool"


class CatalogEntry(BaseModel):
    id: str
    kind: EntryKind
    name: str
    summary: str = ""
    source_url: str = ""
    version: str = ""
    trust: TrustTier
    requires_network: bool = False
    install_hint: str = ""
    tags: list[str] = Field(default_factory=list)


class InstalledRecord(BaseModel):
    id: str
    kind: EntryKind = EntryKind.skill
    version: str = ""
    installed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    source_url: str = ""
    checksum: str = ""
    target_path: str = ""
