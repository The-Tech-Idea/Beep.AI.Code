"""Server capability discovery helpers for the API client."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beep.api.client import BeepAPIClient
    from beep.runtime.server_capabilities import ServerCapabilities


class BeepAPIClientCapabilitiesMixin:
    async def get_capabilities(self) -> ServerCapabilities:
        return await get_capabilities(self)


async def get_capabilities(client: BeepAPIClient) -> ServerCapabilities:
    from beep.runtime.server_capabilities import fetch_server_capabilities

    return await fetch_server_capabilities(client)
