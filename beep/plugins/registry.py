"""Plugin system for extending Beep.AI.Code."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool
from beep.plugins.contracts import (
    BackendProviderPlugin,
    CommandPlugin,
    ContextPlugin,
    Plugin,
    PluginInfo,
    PluginNameConflictError,
    ToolPlugin,
    WorkspaceIntelligencePlugin,
)
from beep.plugins import registry_support


def _validate_tool_schema(tool: BaseTool) -> bool:
    """Validate a plugin tool's JSON schema at load time."""
    return registry_support.validate_tool_schema(tool)


class PluginRegistry:
    """Registry for managing plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._tool_plugins: list[tuple[ToolPlugin, frozenset[str]]] = []
        self._commands: dict[str, CommandPlugin] = {}
        self._context_plugins: list[ContextPlugin] = []
        self._backend_provider_plugins: dict[str, BackendProviderPlugin] = {}
        self._workspace_intelligence_plugins: list[WorkspaceIntelligencePlugin] = []
        self._load_errors: list[str] = []

    def register(self, plugin: Plugin) -> None:
        """Register a plugin."""
        registry_support.register_plugin(self, plugin)

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        registry_support.unregister_plugin(self, name)

    def load_from_file(self, path: Path) -> None:
        """Load a plugin from a Python file."""
        registry_support.load_from_file(self, path)

    def load_from_directory(self, directory: Path) -> int:
        """Load all plugins from a directory. Returns count loaded."""
        return registry_support.load_from_directory(self, directory)

    def get_tools(self, workspace_root: Path | None = None) -> list[BaseTool]:
        """Get all tools from plugins.

        Parameters
        ----------
        workspace_root:
            When provided, passed to each plugin via
            :meth:`ToolPlugin.get_tools_for_workspace` so workspace-aware
            tools can be constructed with the correct path.
        """
        return registry_support.get_tools(self, workspace_root=workspace_root)

    def get_command_descriptions(self) -> dict[str, str]:
        """Get all commands from plugins."""
        return registry_support.get_command_descriptions(self)

    async def handle_plugin_command(self, command: str, args: str) -> str | None:
        """Handle a command from a plugin."""
        return await registry_support.handle_plugin_command(self, command, args)

    def get_context(self) -> str:
        """Get context from all context plugins."""
        return registry_support.get_context(self)

    def get_backend_provider(self, key: str) -> BackendProviderPlugin | None:
        """Return one backend-provider plugin by provider key."""
        return self._backend_provider_plugins.get(key)

    def list_backend_providers(self) -> list[str]:
        """List backend-provider keys contributed by runtime plugins."""
        return sorted(self._backend_provider_plugins)

    def get_workspace_intelligence_capabilities(self, workspace_root: Path) -> list[Any]:
        """Return workspace-intelligence capability reports from runtime plugins."""
        return registry_support.get_workspace_intelligence_capabilities(self, workspace_root)

    def get_workspace_intelligence_tools(self, workspace_root: Path) -> list[BaseTool]:
        """Return workspace-intelligence tools contributed by runtime plugins."""
        return registry_support.get_workspace_intelligence_tools(self, workspace_root)

    def get_semantic_search_adapter(self, workspace_root: Path) -> Any | None:
        """Return the first shared semantic-search adapter exposed by workspace-intelligence plugins."""
        return registry_support.get_semantic_search_adapter(self, workspace_root)

    def get_workspace_intelligence_reports(self, workspace_root: Path) -> list[Any]:
        """Return status reports from runtime workspace-intelligence plugins."""
        return registry_support.get_workspace_intelligence_reports(self, workspace_root)

    def list_plugins(self) -> list[dict[str, str]]:
        """List all loaded plugins."""
        return registry_support.list_plugins(self)

    def get_load_errors(self) -> list[str]:
        """Get plugin loading errors."""
        return registry_support.get_load_errors(self)
