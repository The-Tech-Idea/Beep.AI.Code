"""Typed provider-capability descriptors for autonomous-agent backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beep.config import BeepConfig
from beep.runtime.capabilities import CapabilityFlag


@dataclass(frozen=True)
class ProviderCapabilities:
    """Feature flags for one agent backend/provider."""

    chat_completion: CapabilityFlag
    tool_calling: CapabilityFlag
    streaming: CapabilityFlag
    structured_output: CapabilityFlag
    vision: CapabilityFlag
    embeddings: CapabilityFlag
    local_model_runtime: CapabilityFlag


@dataclass(frozen=True)
class ProviderDescriptor:
    """Human-readable descriptor for the configured autonomous-agent provider."""

    key: str
    display_name: str
    capabilities: ProviderCapabilities


def build_provider_descriptor(
    config: BeepConfig,
    *,
    plugin_registry: Any | None = None,
) -> ProviderDescriptor:
    """Describe the configured autonomous-agent backend/provider."""
    from beep.agent.provider_plugins import get_agent_backend_provider

    return get_agent_backend_provider(
        config.agent_backend,
        plugin_registry=plugin_registry,
    ).describe(config)