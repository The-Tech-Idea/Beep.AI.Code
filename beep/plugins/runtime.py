"""Runtime plugin discovery and loading helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from beep.plugins.discovery import discover_plugin_search_paths
from beep.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


@dataclass
class PluginRuntime:
    """Loaded plugin runtime details for visibility and integration."""

    registry: PluginRegistry
    searched_paths: list[Path]
    loaded_count: int
    discovery_errors: list[str] = field(default_factory=list)


def load_runtime_plugins(workspace_root: Path, *, enabled: bool = True) -> PluginRuntime:
    """Load plugins from configured discovery locations."""
    from beep.app_service import get_app_service

    registry = get_app_service().plugin_registry(workspace_root)
    search_entries, discovery_errors = discover_plugin_search_paths(workspace_root)
    searched_paths = [entry.path for entry in search_entries]
    if not enabled:
        return PluginRuntime(
            registry=registry,
            searched_paths=searched_paths,
            loaded_count=0,
            discovery_errors=discovery_errors,
        )
    loaded_count = 0
    for plugin_dir in searched_paths:
        try:
            loaded_count += registry.load_from_directory(plugin_dir)
        except (PermissionError, OSError) as exc:
            logger.warning("Plugin discovery skipped %s: %s", plugin_dir, exc)
    return PluginRuntime(
        registry=registry,
        searched_paths=searched_paths,
        loaded_count=loaded_count,
        discovery_errors=discovery_errors,
    )
