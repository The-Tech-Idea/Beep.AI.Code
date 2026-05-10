"""Implementation helpers for the plugin registry."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool
from beep.plugins.contracts import (
    BackendProviderPlugin,
    CommandPlugin,
    ContextPlugin,
    Plugin,
    PluginNameConflictError,
    ToolPlugin,
    WorkspaceIntelligencePlugin,
)

logger = logging.getLogger(__name__)


def validate_tool_schema(tool: BaseTool) -> bool:
    """Validate a plugin tool's JSON schema at load time.

    Fails closed when ``jsonschema`` is unavailable so that invalid schemas
    surface as load-time errors instead of silently passing through.
    """
    schema = tool.parameters
    if not isinstance(schema, dict):
        logger.error(
            "Plugin tool '%s' has invalid parameters: expected dict, got %s",
            tool.name,
            type(schema).__name__,
        )
        return False

    try:
        import jsonschema  # type: ignore[import-untyped]
    except ImportError:
        logger.error(
            "Plugin tool '%s' schema validation skipped: install the 'schema' optional "
            "dependency group (pip install beep-ai-code[schema]) to validate plugin schemas",
            tool.name,
        )
        return False

    meta_schema = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["type"],
        },
    }
    try:
        jsonschema.validate(instance=schema, schema=meta_schema)
        return True
    except jsonschema.ValidationError as exc:
        logger.error("Plugin tool '%s' schema invalid: %s", tool.name, exc.message)
        return False


def register_plugin(registry: Any, plugin: Plugin) -> None:
    name = plugin.info.name
    if name in registry._plugins:
        # Idempotent: skip re-registration
        return
    registry._plugins[name] = plugin
    plugin.activate()

    if isinstance(plugin, ToolPlugin):
        valid_names: set[str] = set()
        for tool in plugin.get_tools():
            if validate_tool_schema(tool):
                valid_names.add(tool.name)
            else:
                registry._load_errors.append(
                    f"Tool '{tool.name}' from plugin '{name}' rejected: invalid schema"
                )
        registry._tool_plugins.append((plugin, frozenset(valid_names)))

    if isinstance(plugin, CommandPlugin):
        registry._commands[name] = plugin

    if isinstance(plugin, ContextPlugin):
        registry._context_plugins.append(plugin)

    if isinstance(plugin, BackendProviderPlugin):
        provider_key = plugin.provider_key()
        if provider_key in registry._backend_provider_plugins:
            raise PluginNameConflictError(
                f"Backend provider '{provider_key}' is already registered. "
                "Rename one of the plugins to resolve the conflict."
            )
        registry._backend_provider_plugins[provider_key] = plugin

    if isinstance(plugin, WorkspaceIntelligencePlugin):
        registry._workspace_intelligence_plugins.append(plugin)


def unregister_plugin(registry: Any, name: str) -> None:
    plugin = registry._plugins.pop(name, None)
    if plugin is None:
        return

    plugin.deactivate()
    if isinstance(plugin, ToolPlugin):
        registry._tool_plugins = [
            (current, names) for current, names in registry._tool_plugins if current is not plugin
        ]
    if isinstance(plugin, BackendProviderPlugin):
        registry._backend_provider_plugins = {
            key: provider
            for key, provider in registry._backend_provider_plugins.items()
            if provider is not plugin
        }
    if isinstance(plugin, WorkspaceIntelligencePlugin):
        registry._workspace_intelligence_plugins = [
            current for current in registry._workspace_intelligence_plugins if current is not plugin
        ]


def load_from_file(registry: Any, path: Path) -> None:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load plugin: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    excluded = {
        Plugin,
        ToolPlugin,
        CommandPlugin,
        ContextPlugin,
        BackendProviderPlugin,
        WorkspaceIntelligencePlugin,
    }
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, Plugin)
            and attr not in excluded
            and attr.__module__ == module.__name__
        ):
            registry.register(attr())


def load_from_directory(registry: Any, directory: Path) -> int:
    count = 0
    if not directory.exists():
        return count

    for path in directory.glob("*.py"):
        if path.name.startswith("_"):
            continue
        try:
            registry.load_from_file(path)
            count += 1
        except Exception as exc:
            registry._load_errors.append(f"{path}: {exc}")

    return count


def get_tools(registry: Any, workspace_root: Path | None = None) -> list[BaseTool]:
    result: list[BaseTool] = []
    for plugin, valid_names in registry._tool_plugins:
        for tool in plugin.get_tools_for_workspace(workspace_root):
            if tool.name in valid_names:
                result.append(tool)
    return result


def get_command_descriptions(registry: Any) -> dict[str, str]:
    commands: dict[str, str] = {}
    for plugin in registry._commands.values():
        commands.update(plugin.get_commands())
    return commands


async def handle_plugin_command(registry: Any, command: str, args: str) -> str | None:
    for plugin in registry._commands.values():
        commands = plugin.get_commands()
        if command in commands:
            return await plugin.handle_command(command, args)
    return None


def get_context(registry: Any) -> str:
    parts = []
    for plugin in registry._context_plugins:
        context = plugin.get_context()
        if context:
            parts.append(context)
    return "\n\n".join(parts)


def get_workspace_intelligence_capabilities(registry: Any, workspace_root: Path) -> list[Any]:
    capabilities: list[Any] = []
    for plugin in registry._workspace_intelligence_plugins:
        capability_set = plugin.capabilities(workspace_root=workspace_root)
        if capability_set is not None:
            capabilities.append(capability_set)
    return capabilities


def get_workspace_intelligence_tools(registry: Any, workspace_root: Path) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for plugin in registry._workspace_intelligence_plugins:
        for tool in plugin.get_tools_for_workspace(workspace_root):
            if validate_tool_schema(tool):
                tools.append(tool)
            else:
                registry._load_errors.append(
                    f"Workspace intelligence tool '{tool.name}' from plugin '{plugin.info.name}' rejected: invalid schema"
                )
    return tools


def get_semantic_search_adapter(registry: Any, workspace_root: Path) -> Any | None:
    for plugin in registry._workspace_intelligence_plugins:
        adapter = plugin.get_semantic_search_adapter(workspace_root)
        if adapter is not None:
            return adapter
    return None


def get_workspace_intelligence_reports(registry: Any, workspace_root: Path) -> list[Any]:
    reports: list[Any] = []
    for plugin in registry._workspace_intelligence_plugins:
        report = plugin.get_status_report(workspace_root)
        if report is not None:
            reports.append(report)
    return reports


def list_plugins(registry: Any) -> list[dict[str, str]]:
    return [
        {
            "name": plugin.info.name,
            "version": plugin.info.version,
            "description": plugin.info.description,
            "type": type(plugin).__name__,
        }
        for plugin in registry._plugins.values()
    ]


def get_load_errors(registry: Any) -> list[str]:
    return list(registry._load_errors)
