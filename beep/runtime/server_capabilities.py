"""Server-side capability discovery and caching.

Queries Beep.AI.Server for its enabled services, version, and feature
flags, then caches the result per (server_url, token).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from beep.api.client import BeepAPIClient


@dataclass
class ServerCapabilities:
    """Discovered capabilities of a Beep.AI.Server instance."""

    server_url: str
    server_version: str = ""
    server_name: str = "Beep.AI.Server"

    available: bool = False
    error: str | None = None

    rag_enabled: bool = False
    agents_enabled: bool = False
    mcp_enabled: bool = False
    tooling_enabled: bool = False
    scheduler_enabled: bool = False
    vision_enabled: bool = False
    audio_enabled: bool = False
    document_extraction_enabled: bool = False
    studio_enabled: bool = False
    workflow_engine_enabled: bool = False
    coding_assistant_enabled: bool = False

    services: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    fetched_at: float = 0.0

    def is_beep_server(self) -> bool:
        return self.available and bool(self.server_version)

    def capability_map(self) -> dict[str, bool]:
        return {
            "rag": self.rag_enabled,
            "agents": self.agents_enabled,
            "mcp": self.mcp_enabled,
            "tooling": self.tooling_enabled,
            "scheduler": self.scheduler_enabled,
            "vision": self.vision_enabled,
            "audio": self.audio_enabled,
            "document_extraction": self.document_extraction_enabled,
            "studio": self.studio_enabled,
            "workflow_engine": self.workflow_engine_enabled,
            "coding_assistant": self.coding_assistant_enabled,
        }

    def missing_capabilities(self) -> list[str]:
        return [k for k, v in self.capability_map().items() if not v]

    def has_capability(self, name: str) -> bool:
        return self.capability_map().get(name, False)


_SERVER_CAPABILITIES_CACHE: dict[tuple[str, str | None], ServerCapabilities] = {}
_CACHE_TTL = 300


async def fetch_server_capabilities(client: BeepAPIClient) -> ServerCapabilities:
    url = client._base_url
    token = client._config.api_token
    cache_key = (url, token)

    cached = _SERVER_CAPABILITIES_CACHE.get(cache_key)
    if cached and (time.monotonic() - cached.fetched_at) < _CACHE_TTL:
        return cached

    caps = ServerCapabilities(server_url=url)
    caps.fetched_at = time.monotonic()

    try:
        health = await client.v1_health()
        caps.available = True
        caps.server_version = health.get("version", "")
        caps.server_name = health.get("name", "Beep.AI.Server")
        caps.raw = dict(health)
        caps.services = list(health.get("services", []))
    except Exception as exc:
        caps.error = str(exc)
        _SERVER_CAPABILITIES_CACHE[cache_key] = caps
        return caps

    caps.coding_assistant_enabled = True

    service_set = {s.lower() for s in caps.services}
    caps.rag_enabled = "rag" in service_set
    caps.agents_enabled = "agents" in service_set or "agent" in service_set
    caps.mcp_enabled = "mcp" in service_set
    caps.tooling_enabled = "tooling" in service_set
    caps.scheduler_enabled = "scheduler" in service_set or "job-scheduler" in service_set
    caps.vision_enabled = "vision" in service_set
    caps.audio_enabled = "audio" in service_set
    caps.document_extraction_enabled = "document-extraction" in service_set
    caps.studio_enabled = "studio" in service_set or "agent-studio" in service_set
    caps.workflow_engine_enabled = "workflow-engine" in service_set

    _SERVER_CAPABILITIES_CACHE[cache_key] = caps
    return caps


def clear_capabilities_cache() -> None:
    _SERVER_CAPABILITIES_CACHE.clear()
