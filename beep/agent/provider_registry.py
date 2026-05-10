"""Registry and guidance helpers for autonomous-agent backend providers."""

from __future__ import annotations

import inspect
from typing import Any

from beep.agent.provider_contracts import AgentBackendProvider, ProviderGuidance, ProviderProbeResult
from beep.config import BeepConfig
from beep.plugins.registry import PluginRegistry


def list_agent_backend_providers(
    builtin_providers: dict[str, AgentBackendProvider],
) -> list[AgentBackendProvider]:
    return list(builtin_providers.values())


def _get_runtime_provider(
    key: str,
    *,
    plugin_registry: PluginRegistry | Any | None = None,
) -> Any | None:
    if plugin_registry is None:
        return None
    getter = getattr(plugin_registry, "get_backend_provider", None)
    if getter is None or not callable(getter):
        return None
    return getter(key)


def _provider_source_label(provider: Any) -> str:
    source_label = getattr(provider, "source_label", None)
    if callable(source_label):
        return str(source_label())
    return "plugin"


def _provider_requires_api_key(provider: Any) -> bool | None:
    requires_api_key = getattr(provider, "requires_api_key", None)
    if callable(requires_api_key):
        return requires_api_key()
    return None


def _provider_requires_model(provider: Any) -> bool | None:
    requires_model = getattr(provider, "requires_model", None)
    if callable(requires_model):
        return requires_model()
    return None


def _provider_default_base_url(provider: Any) -> str | None:
    default_base_url = getattr(provider, "default_base_url", None)
    if callable(default_base_url):
        return default_base_url()
    return None


def _provider_configuration_notes(provider: Any, config: BeepConfig) -> tuple[str, ...]:
    notes = getattr(provider, "configuration_notes", None)
    if callable(notes):
        result = notes(config)
        if isinstance(result, tuple):
            return tuple(str(item) for item in result if str(item).strip())
        if isinstance(result, list):
            return tuple(str(item) for item in result if str(item).strip())
    return ("See the provider plugin documentation for configuration details.",)


def get_agent_backend_provider(
    key: str,
    *,
    builtin_providers: dict[str, AgentBackendProvider],
    plugin_registry: PluginRegistry | Any | None = None,
) -> Any:
    runtime_provider = _get_runtime_provider(key, plugin_registry=plugin_registry)
    if runtime_provider is not None:
        return runtime_provider
    try:
        return builtin_providers[key]
    except KeyError as exc:
        raise ValueError(f"Unsupported agent backend: {key}") from exc


def describe_agent_provider_guidance(
    config: BeepConfig,
    *,
    builtin_providers: dict[str, AgentBackendProvider],
    provider_key: str | None = None,
    plugin_registry: PluginRegistry | Any | None = None,
) -> ProviderGuidance:
    key = provider_key or config.agent_backend
    provider = get_agent_backend_provider(
        key,
        builtin_providers=builtin_providers,
        plugin_registry=plugin_registry,
    )
    descriptor = provider.describe(config)
    return ProviderGuidance(
        key=descriptor.key,
        display_name=descriptor.display_name,
        source=_provider_source_label(provider),
        configured=bool(provider.is_configured(config)),
        local_runtime=bool(descriptor.capabilities.local_model_runtime.exists),
        requires_api_key=_provider_requires_api_key(provider),
        requires_model=_provider_requires_model(provider),
        default_base_url=_provider_default_base_url(provider),
        selected=descriptor.key == config.agent_backend,
        notes=_provider_configuration_notes(provider, config),
    )


async def probe_agent_backend_configuration(
    config: BeepConfig,
    *,
    builtin_providers: dict[str, AgentBackendProvider],
    plugin_registry: PluginRegistry | Any | None = None,
) -> ProviderProbeResult:
    provider = get_agent_backend_provider(
        config.agent_backend,
        builtin_providers=builtin_providers,
        plugin_registry=plugin_registry,
    )
    probe = getattr(provider, "probe_configuration", None)
    if probe is None or not callable(probe):
        return ProviderProbeResult(
            supported=False,
            success=False,
            message="This provider does not expose a validation probe.",
        )
    result = probe(config)
    if inspect.isawaitable(result):
        result = await result
    if result is None:
        return ProviderProbeResult(
            supported=False,
            success=False,
            message="This provider does not expose a validation probe.",
        )
    if isinstance(result, ProviderProbeResult):
        return result
    return ProviderProbeResult(
        supported=False,
        success=False,
        message="This provider returned an invalid validation result.",
    )


def list_available_agent_provider_guidance(
    config: BeepConfig,
    *,
    builtin_providers: dict[str, AgentBackendProvider],
    plugin_registry: PluginRegistry | Any | None = None,
) -> list[ProviderGuidance]:
    keys = {provider.key for provider in builtin_providers.values()}
    if plugin_registry is not None:
        list_backend_providers = getattr(plugin_registry, "list_backend_providers", None)
        if callable(list_backend_providers):
            keys.update(str(item) for item in list_backend_providers())
    return [
        describe_agent_provider_guidance(
            config,
            builtin_providers=builtin_providers,
            provider_key=key,
            plugin_registry=plugin_registry,
        )
        for key in sorted(keys)
    ]


def is_agent_backend_configured(
    config: BeepConfig,
    *,
    builtin_providers: dict[str, AgentBackendProvider],
    plugin_registry: PluginRegistry | Any | None = None,
) -> bool:
    provider = get_agent_backend_provider(
        config.agent_backend,
        builtin_providers=builtin_providers,
        plugin_registry=plugin_registry,
    )
    return bool(provider.is_configured(config))