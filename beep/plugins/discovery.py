"""File-backed plugin discovery helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PluginSearchPath:
    """A plugin search path together with its discovery source."""

    path: Path
    source: str


@dataclass(frozen=True)
class PluginManifestLocation:
    """A file-backed location that can contribute plugin search paths."""

    scope: str
    path: Path
    base_dir: Path


def get_plugin_manifest_locations(workspace_root: Path) -> tuple[PluginManifestLocation, ...]:
    """Return the supported user and workspace plugin manifest locations."""
    return (
        PluginManifestLocation(
            scope="user",
            path=Path.home() / ".beepai" / "plugins.json",
            base_dir=Path.home(),
        ),
        PluginManifestLocation(
            scope="workspace",
            path=workspace_root / ".beep" / "plugins.json",
            base_dir=workspace_root,
        ),
    )


def discover_plugin_search_paths(workspace_root: Path) -> tuple[list[PluginSearchPath], list[str]]:
    """Return the default and manifest-backed plugin search paths."""
    search_paths: list[PluginSearchPath] = [
        PluginSearchPath(path=Path.home() / ".beepai" / "plugins", source="user-default"),
        PluginSearchPath(path=workspace_root / ".beep" / "plugins", source="workspace-default"),
    ]
    env_dir = os.environ.get("BEEP_PLUGINS_DIR")
    if env_dir:
        search_paths.append(PluginSearchPath(path=Path(env_dir), source="env:BEEP_PLUGINS_DIR"))

    warnings: list[str] = []
    for location in get_plugin_manifest_locations(workspace_root):
        try:
            raw_paths = _load_manifest_entries(location.path)
        except (OSError, ValueError) as exc:
            warnings.append(f"{location.path}: {exc}")
            continue
        for raw_path in raw_paths:
            search_paths.append(
                PluginSearchPath(
                    path=_resolve_manifest_path(raw_path, location.base_dir),
                    source=f"{location.scope}-manifest",
                )
            )

    return _dedupe_search_paths(search_paths), warnings


def add_plugin_search_path(workspace_root: Path, plugin_path: Path, *, scope: str = "workspace") -> Path:
    """Add a plugin search path to the user or workspace manifest."""
    location = _get_manifest_location(workspace_root, scope)
    try:
        entries = _load_manifest_entries(location.path)
    except FileNotFoundError:
        entries = []

    resolved_path = plugin_path.expanduser()
    if not resolved_path.is_absolute():
        resolved_path = resolved_path.resolve()
    stored_path = _format_path_for_storage(resolved_path, location.base_dir)
    if stored_path not in entries:
        entries.append(stored_path)

    payload = {"plugin_paths": entries}
    location.path.parent.mkdir(parents=True, exist_ok=True)
    location.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return location.path


def _get_manifest_location(workspace_root: Path, scope: str) -> PluginManifestLocation:
    for location in get_plugin_manifest_locations(workspace_root):
        if location.scope == scope:
            return location
    raise ValueError("scope must be 'user' or 'workspace'")


def _load_manifest_entries(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must contain a JSON object")
    raw_paths = payload.get("plugin_paths", [])
    if not isinstance(raw_paths, list) or not all(isinstance(item, str) and item.strip() for item in raw_paths):
        raise ValueError("plugin_paths must be a list of non-empty strings")
    return raw_paths


def _resolve_manifest_path(raw_path: str, base_dir: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _format_path_for_storage(path: Path, base_dir: Path) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()


def _dedupe_search_paths(entries: list[PluginSearchPath]) -> list[PluginSearchPath]:
    deduped: list[PluginSearchPath] = []
    seen: set[Path] = set()
    for entry in entries:
        resolved = entry.path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(PluginSearchPath(path=resolved, source=entry.source))
    return deduped