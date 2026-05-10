"""Shared contracts for autonomous-agent backend providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from beep.agent.backends import AgentModelBackend
from beep.agent.provider_capabilities import ProviderDescriptor
from beep.config import BeepConfig


@dataclass(frozen=True)
class ProviderGuidance:
    """Configuration and discovery details for one agent provider."""

    key: str
    display_name: str
    source: str
    configured: bool
    local_runtime: bool
    requires_api_key: bool | None
    requires_model: bool | None
    default_base_url: str | None
    selected: bool
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ProviderProbeResult:
    """Connectivity probe result for one agent provider configuration."""

    supported: bool
    success: bool
    message: str


class AgentBackendProvider(ABC):
    """Contract for one autonomous-agent backend provider."""

    key: str
    display_name: str

    def source_label(self) -> str:
        """Return the provider source label used in UX surfaces."""
        return "built-in"

    def requires_api_key(self) -> bool | None:
        """Return whether the provider requires an API key."""
        return None

    def requires_model(self) -> bool | None:
        """Return whether the provider requires an explicit model selection."""
        return None

    def default_base_url(self) -> str | None:
        """Return the provider's default base URL when one exists."""
        return None

    def configuration_notes(self, config: BeepConfig) -> tuple[str, ...]:
        """Return provider-specific configuration guidance notes."""
        del config
        return ()

    async def probe_configuration(self, config: BeepConfig) -> ProviderProbeResult:
        """Return a best-effort connectivity probe for this provider."""
        del config
        return ProviderProbeResult(
            supported=False,
            success=False,
            message="This provider does not expose a validation probe.",
        )

    @abstractmethod
    def is_configured(self, config: BeepConfig) -> bool:
        """Return True when the provider has enough configuration to run."""

    @abstractmethod
    def describe(self, config: BeepConfig) -> ProviderDescriptor:
        """Return the provider descriptor for the active configuration."""

    @abstractmethod
    def build_backend(
        self,
        config: BeepConfig,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> AgentModelBackend:
        """Build the runtime backend for this provider."""