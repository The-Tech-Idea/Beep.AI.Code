"""Shared per-workspace runtime initialization."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from beep.chat.command_registry import build_command_registry
from beep.memory.loader import ProjectMemory, load_project_memory
from beep.plugins.registry import PluginRegistry
from beep.plugins.runtime import PluginRuntime, load_runtime_plugins
from beep.rules.loader import LoadedRule, load_rules
from beep.runtime.builtin_workspace_intelligence import (
    CSharpWorkspaceIntelligencePlugin,
    JavaScriptWorkspaceIntelligencePlugin,
    PythonJediWorkspaceIntelligencePlugin,
    SembleWorkspaceIntelligencePlugin,
    TypeScriptWorkspaceIntelligencePlugin,
)
from beep.skills.loader import load_skills
from beep.skills.models import SkillDefinition
from beep.runtime.workspace_intelligence import (
    WorkspaceIntelligenceCapabilities,
    build_workspace_intelligence_capabilities,
    merge_workspace_intelligence_capabilities,
)
from beep.workspace.detector import find_workspace_root


@dataclass(frozen=True)
class WorkspaceRuntime:
    """Shared immutable-ish runtime dependencies for one workspace."""

    workspace: Path
    memory: ProjectMemory
    commands: dict
    plugin_runtime: PluginRuntime
    plugin_commands: dict[str, str]
    semantic_search_adapter: object | None
    workspace_intelligence_capabilities: WorkspaceIntelligenceCapabilities
    rules: list[LoadedRule]
    rule_errors: list[str]
    skills: list[SkillDefinition]
    skill_errors: list[str]
    skill_roots: list[Path]
    # Skills fetched from the Beep.AI.Server (global skills).
    # Set after async fetch during session bootstrap; not part of the cached runtime.
    server_skills: list[SkillDefinition] = None

    def __post_init__(self):
        if self.server_skills is None:
            object.__setattr__(self, "server_skills", [])


def _register_builtin_workspace_intelligence_plugins(registry: PluginRegistry) -> None:
    """Register built-in workspace-intelligence plugins on a runtime registry."""
    registry.register(SembleWorkspaceIntelligencePlugin())
    registry.register(PythonJediWorkspaceIntelligencePlugin())
    registry.register(CSharpWorkspaceIntelligencePlugin())
    registry.register(JavaScriptWorkspaceIntelligencePlugin())
    registry.register(TypeScriptWorkspaceIntelligencePlugin())


def get_workspace_runtime(
    workspace_root: Path | None = None,
    *,
    plugins_enabled: bool = True,
) -> WorkspaceRuntime:
    """Return the cached runtime bundle for a workspace."""
    workspace = workspace_root or find_workspace_root()
    return _get_workspace_runtime(str(workspace.resolve()), plugins_enabled)


def clear_workspace_runtime_cache() -> None:
    """Clear cached runtime bundles, mostly useful for tests."""
    _get_workspace_runtime.cache_clear()


@lru_cache(maxsize=16)
def _get_workspace_runtime(workspace_key: str, plugins_enabled: bool) -> WorkspaceRuntime:
    workspace = Path(workspace_key)
    plugin_runtime = load_runtime_plugins(workspace, enabled=plugins_enabled)
    _register_builtin_workspace_intelligence_plugins(plugin_runtime.registry)
    get_semantic_search_adapter = getattr(
        plugin_runtime.registry, "get_semantic_search_adapter", None
    )
    semantic_search_adapter = (
        get_semantic_search_adapter(workspace) if callable(get_semantic_search_adapter) else None
    )
    workspace_intelligence_capabilities = build_workspace_intelligence_capabilities(
        semantic_search_adapter.availability_report()
        if semantic_search_adapter is not None
        else None
    )
    get_workspace_intelligence_capabilities = getattr(
        plugin_runtime.registry,
        "get_workspace_intelligence_capabilities",
        None,
    )
    if callable(get_workspace_intelligence_capabilities):
        plugin_capabilities = [
            capability
            for capability in get_workspace_intelligence_capabilities(workspace)
            if isinstance(capability, WorkspaceIntelligenceCapabilities)
        ]
        if plugin_capabilities:
            workspace_intelligence_capabilities = merge_workspace_intelligence_capabilities(
                workspace_intelligence_capabilities,
                *plugin_capabilities,
            )
    rules, rule_errors = load_rules(workspace)
    skills, skill_errors, skill_roots = load_skills(workspace)
    return WorkspaceRuntime(
        workspace=workspace,
        memory=load_project_memory(workspace),
        commands=build_command_registry(),
        plugin_runtime=plugin_runtime,
        plugin_commands=plugin_runtime.registry.get_command_descriptions(),
        semantic_search_adapter=semantic_search_adapter,
        workspace_intelligence_capabilities=workspace_intelligence_capabilities,
        rules=rules,
        rule_errors=rule_errors,
        skills=skills,
        skill_errors=skill_errors,
        skill_roots=skill_roots,
    )
