"""Tests for agent tool composition."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

from beep.agent.approval import requires_approval
from beep.agent.tools.semantic_search import build_semble_tools
from beep.agent.tools.factory import build_agent_tools, get_default_tools
from beep.config import MCPServerConfig, MCPToolConfig


def test_default_agent_tools_include_core_workspace_tools() -> None:
    with tempfile.TemporaryDirectory() as td:
        names = {tool.name for tool in get_default_tools(Path(td))}
    assert {"file_read", "file_write", "file_edit", "search", "shell"} <= names
    assert "semantic_search" not in names
    assert "find_related_code" not in names


def test_default_tools_include_new_tools() -> None:
    with tempfile.TemporaryDirectory() as td:
        names = {tool.name for tool in get_default_tools(Path(td))}
    assert "list_directory" in names
    assert "glob_files" in names
    assert "git" in names
    assert "file_read" in names


def test_read_only_mode_omits_write_tools() -> None:
    with tempfile.TemporaryDirectory() as td:
        names = {tool.name for tool in get_default_tools(Path(td), read_only=True)}
    assert "file_write" not in names
    assert "file_edit" not in names
    assert "shell" not in names


def test_read_only_mode_keeps_read_tools() -> None:
    with tempfile.TemporaryDirectory() as td:
        names = {tool.name for tool in get_default_tools(Path(td), read_only=True)}
    assert "file_read" in names
    assert "search" in names
    assert "semantic_search" not in names
    assert "find_related_code" not in names
    assert "list_directory" in names
    assert "glob_files" in names
    assert "git" in names


def test_git_read_subcommands_do_not_require_approval() -> None:
    for sub in ("status", "diff", "log", "show HEAD"):
        assert not requires_approval("git", {"subcommand": sub})


def test_git_write_subcommands_require_approval() -> None:
    for sub in ("add .", "commit -m fix", "stash", "restore file.py", "reset HEAD file.py"):
        assert requires_approval("git", {"subcommand": sub})


def test_git_unknown_arguments_conservative() -> None:
    assert requires_approval("git", None) is True
    assert requires_approval("git", {}) is True


def test_python_rename_requires_approval() -> None:
    assert requires_approval("python_rename", {"file_path": "pkg/sample.py", "line": 2, "new_name": "renamed"})


def test_build_agent_tools_adds_plugin_tools() -> None:
    plugin_tool = SimpleNamespace(name="plugin_tool")
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: [],
            get_tools=lambda workspace_root=None: [plugin_tool],
        )
    )
    with tempfile.TemporaryDirectory() as td:
        tools = build_agent_tools(workspace_root=Path(td), plugin_runtime=runtime)

    assert plugin_tool in tools


def test_build_agent_tools_read_only_omits_write_tools() -> None:
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: list(build_semble_tools(workspace_root=workspace_root)),
            get_tools=lambda workspace_root=None: [],
        )
    )
    with tempfile.TemporaryDirectory() as td:
        names = {t.name for t in build_agent_tools(
            workspace_root=Path(td), plugin_runtime=runtime, read_only=True
        )}
    assert "file_write" not in names
    assert "shell" not in names
    assert "file_read" in names
    assert "semantic_search" in names


def test_build_agent_tools_read_only_filters_unsafe_plugin_tools() -> None:
    safe_tool = SimpleNamespace(name="safe_plugin_tool", read_only_safe=True)
    unsafe_tool = SimpleNamespace(name="unsafe_plugin_tool", read_only_safe=False)
    implicit_tool = SimpleNamespace(name="implicit_plugin_tool")
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: [unsafe_tool],
            get_tools=lambda workspace_root=None: [safe_tool, unsafe_tool, implicit_tool],
        )
    )
    with tempfile.TemporaryDirectory() as td:
        tools = build_agent_tools(
            workspace_root=Path(td),
            plugin_runtime=runtime,
            read_only=True,
        )

    assert safe_tool in tools
    assert unsafe_tool not in tools
    assert implicit_tool not in tools


def test_build_agent_tools_read_only_omits_mcp_tools_by_default() -> None:
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: [],
            get_tools=lambda workspace_root=None: [],
        )
    )
    mcp_servers = [
        MCPServerConfig(
            name="local-mcp",
            command="python",
            tools=[MCPToolConfig(name="query_db", parameters={"type": "object"})],
        )
    ]
    with tempfile.TemporaryDirectory() as td:
        names = {
            tool.name
            for tool in build_agent_tools(
                workspace_root=Path(td),
                plugin_runtime=runtime,
                read_only=True,
                mcp_enabled=True,
                mcp_servers=mcp_servers,
            )
        }

    assert "query_db" not in names


def test_build_agent_tools_read_only_keeps_explicitly_safe_mcp_tools() -> None:
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: [],
            get_tools=lambda workspace_root=None: [],
        )
    )
    mcp_servers = [
        MCPServerConfig(
            name="local-mcp",
            command="python",
            tools=[
                MCPToolConfig(
                    name="query_db",
                    parameters={"type": "object"},
                    read_only_safe=True,
                )
            ],
        )
    ]
    with tempfile.TemporaryDirectory() as td:
        tools = build_agent_tools(
            workspace_root=Path(td),
            plugin_runtime=runtime,
            read_only=True,
            mcp_enabled=True,
            mcp_servers=mcp_servers,
        )

    query_tool = next(tool for tool in tools if tool.name == "query_db")
    assert query_tool.read_only_safe is True
    assert getattr(query_tool, "requires_human_approval", None) is True


def test_build_agent_tools_omits_semble_tools_when_registry_has_no_workspace_intelligence_tools() -> None:
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: [],
            get_tools=lambda workspace_root=None: [],
        )
    )
    with tempfile.TemporaryDirectory() as td:
        names = {
            t.name
            for t in build_agent_tools(
                workspace_root=Path(td),
                plugin_runtime=runtime,
            )
        }

    assert "search" in names
    assert "semantic_search" not in names
    assert "find_related_code" not in names


def test_build_agent_tools_adds_workspace_intelligence_plugin_tools() -> None:
    plugin_tool = SimpleNamespace(name="plugin_lsp_tool")
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: [plugin_tool],
            get_tools=lambda workspace_root=None: [],
        )
    )
    with tempfile.TemporaryDirectory() as td:
        tools = build_agent_tools(workspace_root=Path(td), plugin_runtime=runtime)

    assert plugin_tool in tools


def test_build_agent_tools_includes_semble_tools_via_workspace_intelligence_plugin_path() -> None:
    runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_tools=lambda workspace_root: list(build_semble_tools(workspace_root=workspace_root)),
            get_tools=lambda workspace_root=None: [],
        )
    )
    with tempfile.TemporaryDirectory() as td:
        names = {t.name for t in build_agent_tools(workspace_root=Path(td), plugin_runtime=runtime)}

    assert "semantic_search" in names
    assert "find_related_code" in names
