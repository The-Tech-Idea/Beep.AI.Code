"""Local catalog of specialty layers and agents fetched from the server.

Caches available layers and agent definitions so the chat REPL can:
- Show available agents/layers to the user
- Allow switching between agents via /agent command
- Apply profile-specific system prompts based on layer knowledge
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LayerInfo:
    """Lightweight representation of a specialty layer from the server."""

    id: str
    name: str
    type: str                       # "coding", "business", "design", "rules"
    domain: str                     # "react", "python", "legal", etc.
    description: str
    enabled: bool = True
    loaded: bool = False
    tools: list[str] = field(default_factory=list)
    rag_collections: list[str] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)
    rules_layers: list[str] = field(default_factory=list)


@dataclass
class AgentInfo:
    """Lightweight representation of an agent definition."""

    id: str
    name: str
    description: str
    framework: str = "langgraph"
    is_template: bool = False
    layer_id: str | None = None


class LayerCatalog:
    """Local cache of specialty layers and agents from the server.

    Usage:
        catalog = LayerCatalog()
        await catalog.refresh(client)
        layers = catalog.for_profile("team_lead_dev")
    """

    def __init__(self) -> None:
        self._layers: dict[str, LayerInfo] = {}
        self._agents: dict[str, AgentInfo] = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def refresh(self, client: Any, api_token: str | None = None) -> None:
        """Fetch layers and agents from the server."""
        headers = {}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"

        try:
            import httpx
            base = client._base_url if hasattr(client, "_base_url") else "http://localhost:5000"

            async with httpx.AsyncClient(base_url=base.rstrip("/"), headers=headers, timeout=10.0) as http:
                # Fetch layers
                resp = await http.get("/v1/api/specialty-layers")
                if resp.status_code == 200:
                    data = resp.json()
                    for l in data.get("layers", []):
                        self._layers[l["id"]] = LayerInfo(
                            id=l["id"],
                            name=l["name"],
                            type=l["type"],
                            domain=l["domain"],
                            description=l["description"],
                            enabled=l["enabled"],
                            loaded=l["loaded"],
                        )

            self._loaded = True
            logger.debug(f"Loaded {len(self._layers)} layers from server")

        except Exception as e:
            logger.warning(f"Failed to refresh layer catalog: {e}")

    def for_profile(self, profile_id: str) -> list[LayerInfo]:
        """Get layers relevant to a specific profile."""
        profile_layers: dict[str, list[str]] = {
            "team_lead_dev": ["react_developer", "vue_developer", "blazor_developer",
                              "wpf_developer", "maui_developer", "flask_developer",
                              "django_developer", "fastapi_developer",
                              "clean_code_rules", "domain_architecture_rules"],
            "business_analyst": ["document_analyst", "spreadsheet_analyst",
                                "requirements_analyst", "process_mapper"],
            "team_lead_biz": ["contract_reviewer", "document_writer", "spreadsheet_analyst",
                             "catalog_assistant", "reservoir_analyst", "drilling_optimizer"],
            "content_creator": ["web_designer", "winforms_designer", "design_reviewer"],
            "student": ["quick_chat", "simple_rag"],
        }
        relevant = profile_layers.get(profile_id, [])
        return [l for l in self._layers.values() if l.id in relevant and l.enabled]

    def all_layers(self) -> list[LayerInfo]:
        """Get all loaded layers."""
        return list(self._layers.values())

    def get_layer(self, layer_id: str) -> LayerInfo | None:
        """Get a specific layer by ID."""
        return self._layers.get(layer_id)

    def search(self, query: str) -> list[LayerInfo]:
        """Search layers by name, domain, or description."""
        q = query.lower()
        return [
            l for l in self._layers.values()
            if q in l.name.lower() or q in l.domain.lower() or q in l.description.lower()
        ]


# Singleton
_catalog: LayerCatalog | None = None


def get_layer_catalog() -> LayerCatalog:
    """Get the singleton layer catalog."""
    global _catalog
    if _catalog is None:
        _catalog = LayerCatalog()
    return _catalog
