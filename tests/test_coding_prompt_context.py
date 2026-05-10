"""Tests for shared Coding Assistant prompt context."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from beep.coding.prompt_context import build_workspace_system_prompt
from beep.rules.loader import LoadedRule


def test_workspace_system_prompt_includes_project_memory_and_rules(monkeypatch) -> None:
    _section = "## Project Instructions\n\nPrefer small focused patches."
    memory = SimpleNamespace(
        to_system_prompt=lambda: _section,
        to_prompt_section=lambda: _section,
    )
    monkeypatch.setattr("beep.coding.prompt_context.load_project_memory", lambda _root: memory)
    monkeypatch.setattr(
        "beep.rules.loader.load_rules",
        lambda _root: ([LoadedRule(Path("AGENTS.md"), "Keep auth boundaries strict.")], []),
    )

    prompt = build_workspace_system_prompt("assistant", "C:/repo")

    assert "Project Instructions" in prompt
    assert "Prefer small focused patches." in prompt
    assert "Active Rules" in prompt
    assert "Keep auth boundaries strict." in prompt


def test_workspace_system_prompt_includes_extra_sections(monkeypatch) -> None:
    memory = SimpleNamespace(to_system_prompt=lambda: "", to_prompt_section=lambda: "")
    monkeypatch.setattr("beep.coding.prompt_context.load_project_memory", lambda _root: memory)
    monkeypatch.setattr("beep.rules.loader.load_rules", lambda _root: ([], []))

    prompt = build_workspace_system_prompt(
        "assistant",
        "C:/repo",
        extra_sections=["## Plugin Context\n\nUse plugin rules."],
    )

    assert "Plugin Context" in prompt
    assert "Use plugin rules." in prompt


def test_agent_prompt_includes_capability_aware_workflow_guidance(monkeypatch) -> None:
    memory = SimpleNamespace(to_system_prompt=lambda: "", to_prompt_section=lambda: "")
    monkeypatch.setattr("beep.coding.prompt_context.load_project_memory", lambda _root: memory)
    monkeypatch.setattr("beep.rules.loader.load_rules", lambda _root: ([], []))

    prompt = build_workspace_system_prompt(
        "agent",
        "C:/repo",
        tools=[
            SimpleNamespace(name="file_read", description="Read a file."),
            SimpleNamespace(name="search", description="Search the workspace."),
            SimpleNamespace(name="semantic_search", description="Semantic search."),
            SimpleNamespace(name="find_related_code", description="Find related code."),
            SimpleNamespace(name="python_definition", description="Python definitions."),
            SimpleNamespace(name="python_rename", description="Rename a Python symbol."),
        ],
    )

    assert "Active Workflow Guidance" in prompt
    assert "Use `semantic_search` or `find_related_code` first" in prompt
    assert "`python_rename` mutates files" in prompt


def test_agent_prompt_falls_back_when_semantic_and_lsp_tools_missing(monkeypatch) -> None:
    memory = SimpleNamespace(to_system_prompt=lambda: "", to_prompt_section=lambda: "")
    monkeypatch.setattr("beep.coding.prompt_context.load_project_memory", lambda _root: memory)
    monkeypatch.setattr("beep.rules.loader.load_rules", lambda _root: ([], []))

    prompt = build_workspace_system_prompt(
        "agent",
        "C:/repo",
        tools=[
            SimpleNamespace(name="file_read", description="Read a file."),
            SimpleNamespace(name="search", description="Search the workspace."),
        ],
    )

    assert "Semantic retrieval is unavailable in this workspace" in prompt
    assert "LSP-style symbol workflows are unavailable here" in prompt
