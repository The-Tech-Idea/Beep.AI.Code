"""Plugin contracts for extending Beep.AI.Code."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool


class PluginNameConflictError(Exception):
    """Raised when two plugins share the same name."""


@dataclass
class PluginInfo:
    """Metadata for a plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""


class Plugin(ABC):
    """Base class for plugins."""

    info = PluginInfo(name="unnamed")

    @abstractmethod
    def activate(self) -> None:
        """Called when plugin is loaded."""

    def deactivate(self) -> None:
        """Called when plugin is unloaded."""


class ToolPlugin(Plugin):
    """Plugin that provides agent tools."""

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """Return tools provided by this plugin."""

    def get_tools_for_workspace(self, workspace_root: Path | None = None) -> list[BaseTool]:
        """Return tools, optionally constructed with workspace_root context."""
        del workspace_root
        return self.get_tools()


class CommandPlugin(Plugin):
    """Plugin that provides slash commands."""

    @abstractmethod
    def get_commands(self) -> dict[str, str]:
        """Return command name -> description mapping."""

    @abstractmethod
    async def handle_command(self, command: str, args: str) -> str | None:
        """Handle a slash command. Return response or None."""


class ContextPlugin(Plugin):
    """Plugin that provides additional context."""

    @abstractmethod
    def get_context(self) -> str:
        """Return context string to inject into prompts."""


class BackendProviderPlugin(Plugin):
    """Plugin that provides an autonomous-agent backend/provider."""

    def source_label(self) -> str:
        """Return the provider source label shown in CLI/provider UX."""
        return "plugin"

    def requires_api_key(self) -> bool | None:
        """Return whether the provider requires an API key."""
        return None

    def requires_model(self) -> bool | None:
        """Return whether the provider requires an explicit model selection."""
        return None

    def default_base_url(self) -> str | None:
        """Return the provider's default base URL when one exists."""
        return None

    def configuration_notes(self, config: Any) -> tuple[str, ...]:
        """Return provider-specific configuration guidance notes."""
        del config
        return ()

    def probe_configuration(self, config: Any) -> Any:
        """Return a best-effort configuration probe result, or None when unsupported."""
        del config
        return None

    @abstractmethod
    def provider_key(self) -> str:
        """Return the provider key used in config.agent_backend."""

    @abstractmethod
    def is_configured(self, config: Any) -> bool:
        """Return True when the provider has enough configuration to run."""

    @abstractmethod
    def describe(self, config: Any) -> Any:
        """Return the provider descriptor for the active configuration."""

    @abstractmethod
    def build_backend(
        self,
        config: Any,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> Any:
        """Build the provider-specific autonomous-agent backend."""


class WorkspaceIntelligencePlugin(Plugin):
    """Plugin that contributes workspace-intelligence capabilities and tools."""

    @abstractmethod
    def capabilities(self, *, workspace_root: Path) -> Any:
        """Return capability descriptors for the given workspace."""

    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]:
        """Return workspace-intelligence tools for the given workspace."""
        del workspace_root
        return []

    def get_semantic_search_adapter(self, workspace_root: Path) -> Any | None:
        """Return a shared semantic-search adapter for the given workspace when available."""
        del workspace_root
        return None

    def get_status_report(self, workspace_root: Path) -> Any | None:
        """Return a workspace-intelligence status report for the given workspace."""
        del workspace_root
        return None