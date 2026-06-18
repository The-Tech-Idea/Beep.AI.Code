from __future__ import annotations

from unittest.mock import AsyncMock, patch

from beep.api.client import BeepAPIClient
from beep.config import BeepConfig
from beep.runtime.server_capabilities import (
    ServerCapabilities,
    clear_capabilities_cache,
    fetch_server_capabilities,
)


def test_server_capabilities_defaults() -> None:
    caps = ServerCapabilities(server_url="http://localhost:8000")
    assert not caps.available
    assert caps.server_version == ""
    assert caps.is_beep_server() is False
    assert caps.capability_map() == {
        "rag": False,
        "agents": False,
        "mcp": False,
        "tooling": False,
        "scheduler": False,
        "vision": False,
        "audio": False,
        "document_extraction": False,
        "studio": False,
        "workflow_engine": False,
        "coding_assistant": False,
    }
    assert len(caps.missing_capabilities()) == 11


def test_fetch_capabilities_from_health_response(mock_config: BeepConfig) -> None:
    clear_capabilities_cache()
    client = BeepAPIClient(mock_config)
    health_response = {
        "version": "2.5.0",
        "name": "Beep.AI.Server",
        "services": ["rag", "agents", "mcp", "coding_assistant"],
    }
    with patch.object(client, "v1_health", new=AsyncMock(return_value=health_response)):
        import asyncio

        caps = asyncio.run(fetch_server_capabilities(client))

    assert caps.is_beep_server()
    assert caps.server_version == "2.5.0"
    assert caps.rag_enabled is True
    assert caps.agents_enabled is True
    assert caps.mcp_enabled is True
    assert caps.coding_assistant_enabled is True
    assert caps.tooling_enabled is False
    assert caps.has_capability("rag") is True
    assert caps.has_capability("tooling") is False


def test_fetch_capabilities_when_server_unreachable(mock_config: BeepConfig) -> None:
    clear_capabilities_cache()
    client = BeepAPIClient(mock_config)
    with patch.object(client, "v1_health", new=AsyncMock(side_effect=ConnectionError("refused"))):
        import asyncio

        caps = asyncio.run(fetch_server_capabilities(client))

    assert not caps.available
    assert caps.error == "refused"
    assert caps.is_beep_server() is False


def test_capabilities_cached_within_ttl(mock_config: BeepConfig) -> None:
    clear_capabilities_cache()
    client = BeepAPIClient(mock_config)
    health_response = {"version": "1.0.0", "services": ["mcp"]}

    with patch.object(client, "v1_health", new=AsyncMock(return_value=health_response)):
        import asyncio

        caps1 = asyncio.run(fetch_server_capabilities(client))
        caps2 = asyncio.run(fetch_server_capabilities(client))

    assert caps1.mcp_enabled is True
    assert caps2.mcp_enabled is True
    assert caps1.fetched_at == caps2.fetched_at


def test_client_get_capabilities_mixin(mock_config: BeepConfig) -> None:
    clear_capabilities_cache()
    client = BeepAPIClient(mock_config)
    health_response = {"version": "3.0.0", "services": ["rag", "agents"]}

    with patch.object(client, "v1_health", new=AsyncMock(return_value=health_response)):
        import asyncio

        caps = asyncio.run(client.get_capabilities())

    assert caps.server_version == "3.0.0"
    assert caps.rag_enabled is True
    assert caps.agents_enabled is True
