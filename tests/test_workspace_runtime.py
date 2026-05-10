"""Tests for shared workspace runtime initialization."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from beep.runtime.capabilities import CapabilityFlag
from beep.runtime.builtin_workspace_intelligence import PythonJediWorkspaceIntelligencePlugin, SembleWorkspaceIntelligencePlugin
from beep.runtime.workspace_intelligence import LSPCapabilities, SemanticSearchCapabilities, WorkspaceIntelligenceCapabilities
from beep.runtime.workspace import (
    _register_builtin_workspace_intelligence_plugins,
    clear_workspace_runtime_cache,
    get_workspace_runtime,
)


def test_register_builtin_workspace_intelligence_plugins_adds_semble_and_python_jedi() -> None:
    registered: list[object] = []
    registry = SimpleNamespace(register=lambda plugin: registered.append(plugin))

    _register_builtin_workspace_intelligence_plugins(registry)

    assert any(isinstance(plugin, SembleWorkspaceIntelligencePlugin) for plugin in registered)
    assert any(isinstance(plugin, PythonJediWorkspaceIntelligencePlugin) for plugin in registered)


def test_workspace_runtime_is_cached_per_workspace_and_plugin_mode(
    monkeypatch,
) -> None:
    import tempfile

    clear_workspace_runtime_cache()
    calls = {"plugins": 0, "semantic_search": 0, "builtins": 0}

    monkeypatch.setattr(
        "beep.runtime.workspace.load_project_memory",
        lambda _root: SimpleNamespace(to_system_prompt=lambda: ""),
    )
    monkeypatch.setattr("beep.runtime.workspace.build_command_registry", lambda: {})

    def _load_plugins(_root: Path, *, enabled: bool = True):
        calls["plugins"] += 1
        registry = SimpleNamespace(
            get_command_descriptions=lambda: {},
            get_context=lambda: "",
            get_workspace_intelligence_capabilities=lambda workspace_root: [],
            get_semantic_search_adapter=lambda workspace_root: _get_semantic_search_adapter(workspace_root),
        )
        return SimpleNamespace(registry=registry, enabled=enabled)

    monkeypatch.setattr("beep.runtime.workspace.load_runtime_plugins", _load_plugins)
    monkeypatch.setattr("beep.runtime.workspace.load_rules", lambda _root: ([], []))
    monkeypatch.setattr("beep.runtime.workspace.load_skills", lambda _root: ([], [], []))

    def _get_semantic_search_adapter(root: Path):
        calls["semantic_search"] += 1
        return SimpleNamespace(
            workspace_root=root,
            availability_report=lambda: {"available": True, "error": None},
        )

    monkeypatch.setattr(
        "beep.runtime.workspace._register_builtin_workspace_intelligence_plugins",
        lambda registry: calls.__setitem__("builtins", calls["builtins"] + 1),
    )

    with tempfile.TemporaryDirectory() as td:
        workspace_root = Path(td)
        first = get_workspace_runtime(workspace_root, plugins_enabled=True)
        second = get_workspace_runtime(workspace_root, plugins_enabled=True)
        third = get_workspace_runtime(workspace_root, plugins_enabled=False)

    assert first is second
    assert third is not first
    assert calls["plugins"] == 2
    assert calls["semantic_search"] == 2
    assert calls["builtins"] == 2
    assert first.semantic_search_adapter is second.semantic_search_adapter
    assert first.workspace_intelligence_capabilities.semantic_search.semantic_search.exists is True
    assert third.workspace_intelligence_capabilities.semantic_search.semantic_search.exists is True
    clear_workspace_runtime_cache()


def test_workspace_runtime_merges_workspace_intelligence_plugin_capabilities(monkeypatch) -> None:
    import tempfile

    clear_workspace_runtime_cache()
    monkeypatch.setattr(
        "beep.runtime.workspace.load_project_memory",
        lambda _root: SimpleNamespace(to_system_prompt=lambda: ""),
    )
    monkeypatch.setattr("beep.runtime.workspace.build_command_registry", lambda: {})
    monkeypatch.setattr(
        "beep.runtime.workspace.load_runtime_plugins",
        lambda _root, *, enabled=True: SimpleNamespace(
            registry=SimpleNamespace(
                get_command_descriptions=lambda: {},
                get_context=lambda: "",
                get_workspace_intelligence_capabilities=lambda workspace_root: [
                    WorkspaceIntelligenceCapabilities(
                        semantic_search=SemanticSearchCapabilities(
                            semantic_search=CapabilityFlag(False, "Plugin semantic search unavailable."),
                            find_related=CapabilityFlag(False, "Plugin related search unavailable."),
                            local_indexing=CapabilityFlag(False, "Plugin local indexing unavailable."),
                            remote_git_indexing=CapabilityFlag(False, "Plugin remote indexing unavailable."),
                            hybrid_mode=CapabilityFlag(False, "Plugin hybrid search unavailable."),
                            semantic_mode=CapabilityFlag(False, "Plugin semantic mode unavailable."),
                            bm25_mode=CapabilityFlag(False, "Plugin BM25 unavailable."),
                            language_filters=CapabilityFlag(False, "Plugin language filters unavailable."),
                            path_filters=CapabilityFlag(False, "Plugin path filters unavailable."),
                            index_stats=CapabilityFlag(False, "Plugin index stats unavailable."),
                        ),
                        lsp=LSPCapabilities(
                            diagnostics=CapabilityFlag(True, "Plugin diagnostics available."),
                            hover=CapabilityFlag(True, "Plugin hover available."),
                            definition=CapabilityFlag(False, "Plugin definition unavailable."),
                            references=CapabilityFlag(False, "Plugin references unavailable."),
                            rename=CapabilityFlag(False, "Plugin rename unavailable."),
                            workspace_symbols=CapabilityFlag(False, "Plugin workspace symbols unavailable."),
                            code_actions=CapabilityFlag(False, "Plugin code actions unavailable."),
                            formatting=CapabilityFlag(False, "Plugin formatting unavailable."),
                        ),
                    )
                ],
                get_semantic_search_adapter=lambda workspace_root: SimpleNamespace(
                    workspace_root=workspace_root,
                    availability_report=lambda: {"available": True, "error": None},
                ),
            ),
            enabled=enabled,
        ),
    )
    monkeypatch.setattr("beep.runtime.workspace.load_rules", lambda _root: ([], []))
    monkeypatch.setattr("beep.runtime.workspace.load_skills", lambda _root: ([], [], []))
    monkeypatch.setattr(
        "beep.runtime.workspace._register_builtin_workspace_intelligence_plugins",
        lambda registry: None,
    )

    with tempfile.TemporaryDirectory() as td:
        runtime = get_workspace_runtime(Path(td), plugins_enabled=True)

    assert runtime.workspace_intelligence_capabilities.semantic_search.semantic_search.exists is True
    assert runtime.workspace_intelligence_capabilities.lsp.diagnostics.exists is True
    assert "Plugin diagnostics available." in runtime.workspace_intelligence_capabilities.lsp.diagnostics.notes
    clear_workspace_runtime_cache()
