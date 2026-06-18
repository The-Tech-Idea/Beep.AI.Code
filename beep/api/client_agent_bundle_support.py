"""Portable agent bundle helpers for the API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from beep.api.endpoints import V1_API_AGENTS_BUNDLES_IMPORT

if TYPE_CHECKING:
    from beep.api.client import BeepAPIClient


class BeepAPIClientAgentBundleMixin:
    async def import_agent_bundle(
        self,
        bundle: dict[str, Any],
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        return await import_agent_bundle(self, bundle=bundle, overwrite=overwrite)


async def import_agent_bundle(
    client: BeepAPIClient,
    *,
    bundle: dict[str, Any],
    overwrite: bool = False,
) -> dict[str, Any]:
    payload = {
        "bundle": bundle,
        "overwrite": overwrite,
    }
    return await client._request(
        "POST",
        V1_API_AGENTS_BUNDLES_IMPORT,
        json=payload,
    )
