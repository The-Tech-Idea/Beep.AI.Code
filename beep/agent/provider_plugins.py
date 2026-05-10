"""Built-in provider contract and registry for autonomous-agent backends."""

from __future__ import annotations

import httpx

from typing import Any

from beep.agent.provider_builtin_beep import BeepBackendProvider
from beep.agent.provider_builtin_anthropic import AnthropicBackendProvider
from beep.agent.provider_builtin_openrouter import OpenRouterBackendProvider
from beep.agent.provider_builtin_openai import (
    LMStudioBackendProvider,
    OllamaBackendProvider,
    OpenAIBackendProvider,
    OpenAICompatibleBackendProvider,
)
from beep.agent.provider_contracts import AgentBackendProvider, ProviderGuidance, ProviderProbeResult
from beep.agent.provider_registry import (
    describe_agent_provider_guidance as _describe_agent_provider_guidance,
    get_agent_backend_provider as _get_agent_backend_provider,
    is_agent_backend_configured as _is_agent_backend_configured,
    list_agent_backend_providers as _list_agent_backend_providers,
    list_available_agent_provider_guidance as _list_available_agent_provider_guidance,
    probe_agent_backend_configuration as _probe_agent_backend_configuration,
)
from beep.config import BeepConfig
from beep.plugins.registry import PluginRegistry


_BUILTIN_AGENT_BACKEND_PROVIDERS: dict[str, AgentBackendProvider] = {
    provider.key: provider
    for provider in (
        BeepBackendProvider(),
        AnthropicBackendProvider(),
        OpenAIBackendProvider(),
        OpenRouterBackendProvider(),
        OpenAICompatibleBackendProvider(),
        LMStudioBackendProvider(),
        OllamaBackendProvider(),
    )
}


def list_agent_backend_providers() -> list[AgentBackendProvider]:
    """Return the built-in autonomous-agent backend providers."""
    return _list_agent_backend_providers(_BUILTIN_AGENT_BACKEND_PROVIDERS)


def get_agent_backend_provider(
    key: str,
    *,
    plugin_registry: PluginRegistry | Any | None = None,
) -> Any:
    """Return one provider by key."""
    return _get_agent_backend_provider(
        key,
        builtin_providers=_BUILTIN_AGENT_BACKEND_PROVIDERS,
        plugin_registry=plugin_registry,
    )


def describe_agent_provider_guidance(
    config: BeepConfig,
    *,
    provider_key: str | None = None,
    plugin_registry: PluginRegistry | Any | None = None,
) -> ProviderGuidance:
    """Return CLI-friendly guidance for one provider."""
    return _describe_agent_provider_guidance(
        config,
        builtin_providers=_BUILTIN_AGENT_BACKEND_PROVIDERS,
        provider_key=provider_key,
        plugin_registry=plugin_registry,
    )


async def probe_agent_backend_configuration(
    config: BeepConfig,
    *,
    plugin_registry: PluginRegistry | Any | None = None,
) -> ProviderProbeResult:
    """Run the selected provider's best-effort connectivity probe."""
    return await _probe_agent_backend_configuration(
        config,
        builtin_providers=_BUILTIN_AGENT_BACKEND_PROVIDERS,
        plugin_registry=plugin_registry,
    )


def list_available_agent_provider_guidance(
    config: BeepConfig,
    *,
    plugin_registry: PluginRegistry | Any | None = None,
) -> list[ProviderGuidance]:
    """Return discovery/configuration guidance for built-in and runtime providers."""
    return _list_available_agent_provider_guidance(
        config,
        builtin_providers=_BUILTIN_AGENT_BACKEND_PROVIDERS,
        plugin_registry=plugin_registry,
    )


def is_agent_backend_configured(
    config: BeepConfig,
    *,
    plugin_registry: PluginRegistry | Any | None = None,
) -> bool:
    """Return True when the selected provider has enough configuration to run."""
    return _is_agent_backend_configured(
        config,
        builtin_providers=_BUILTIN_AGENT_BACKEND_PROVIDERS,
        plugin_registry=plugin_registry,
    )
