"""Phase 9 tests: Plugin System & MCP Bridge."""

from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from beep.agent.tools.base import BaseTool
from beep.agent.tools.factory import build_agent_tools, get_default_tools
from beep.agent.tools.file_read import FileReadTool
from beep.agent.tools.search import SearchTool
from beep.agent.tools.shell import ShellTool
from beep.plugins.registry import (
    PluginInfo,
    PluginNameConflictError,
    PluginRegistry,
    ToolPlugin,
)
from beep.plugins.runtime import PluginRuntime, load_runtime_plugins


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeTool(BaseTool):
    """Minimal tool with a valid schema."""

    def __init__(self, name: str, category: str = "misc") -> None:
        self._name = name
        self._cat = category

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "test tool"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "value": {"type": "string", "description": "A value"},
        }

    @property
    def category(self) -> str:
        return self._cat

    async def execute(self, **kwargs: Any):  # type: ignore[override]
        from beep.agent.tools.base import ToolResult

        return ToolResult(success=True, output="ok")


class _BadSchemaTool(BaseTool):
    """Tool whose parameters property is not a dict."""

    @property
    def name(self) -> str:
        return "bad_schema_tool"

    @property
    def description(self) -> str:
        return "bad schema"

    @property
    def parameters(self) -> Any:  # type: ignore[override]
        return ["not", "a", "dict"]

    async def execute(self, **kwargs: Any):  # type: ignore[override]
        from beep.agent.tools.base import ToolResult

        return ToolResult(success=True, output="")


class _SimpleToolPlugin(ToolPlugin):
    """Plugin that exposes a single tool with a valid schema."""

    def __init__(self, tool_name: str = "my_tool", plugin_name: str = "my_plugin") -> None:
        self.info = PluginInfo(name=plugin_name)
        self._tool = _FakeTool(tool_name)

    def activate(self) -> None:
        pass

    def get_tools(self) -> list[BaseTool]:
        return [self._tool]


class _WorkspaceAwarePlugin(ToolPlugin):
    """Plugin that records the workspace_root it received."""

    def __init__(self) -> None:
        self.info = PluginInfo(name="ws_aware_plugin")
        self.received_workspace_root: Path | None = None

    def activate(self) -> None:
        pass

    def get_tools(self) -> list[BaseTool]:
        return [_FakeTool("ws_tool")]

    def get_tools_for_workspace(self, workspace_root: Path | None = None) -> list[BaseTool]:
        self.received_workspace_root = workspace_root
        return [_FakeTool("ws_tool")]


class _BadSchemaPlugin(ToolPlugin):
    """Plugin whose single tool has an invalid schema."""

    def __init__(self) -> None:
        self.info = PluginInfo(name="bad_schema_plugin")

    def activate(self) -> None:
        pass

    def get_tools(self) -> list[BaseTool]:
        return [_BadSchemaTool()]


# Helper: build a minimal PluginRuntime dataclass
def _make_runtime(wp: Path, registry: PluginRegistry | None = None) -> PluginRuntime:
    if registry is None:
        registry = PluginRegistry()
    return PluginRuntime(registry=registry, searched_paths=[], loaded_count=0)


# ---------------------------------------------------------------------------
# TestPluginNameConflict
# ---------------------------------------------------------------------------


class TestPluginNameConflict:
    def test_register_same_name_twice_raises(self) -> None:
        registry = PluginRegistry()
        registry.register(_SimpleToolPlugin("t1", "plugin_alpha"))
        with pytest.raises(PluginNameConflictError):
            registry.register(_SimpleToolPlugin("t2", "plugin_alpha"))

    def test_different_names_both_registered(self) -> None:
        registry = PluginRegistry()
        registry.register(_SimpleToolPlugin("t1", "plugin_a"))
        registry.register(_SimpleToolPlugin("t2", "plugin_b"))
        tools = registry.get_tools()
        names = [t.name for t in tools]
        assert "t1" in names
        assert "t2" in names


# ---------------------------------------------------------------------------
# TestSchemaValidation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_valid_schema_tool_accepted(self) -> None:
        registry = PluginRegistry()
        registry.register(_SimpleToolPlugin())
        assert len(registry.get_tools()) == 1
        assert not registry.get_load_errors()

    def test_invalid_schema_tool_rejected(self) -> None:
        """Tool with non-dict parameters is rejected regardless of jsonschema."""
        registry = PluginRegistry()
        registry.register(_BadSchemaPlugin())
        # The tool should be rejected; registry should report an error
        assert len(registry.get_tools()) == 0
        assert len(registry.get_load_errors()) == 1
        assert "bad_schema_tool" in registry.get_load_errors()[0]

    def test_invalid_schema_does_not_raise(self) -> None:
        """Plugin registration itself should not raise for bad tool schemas."""
        registry = PluginRegistry()
        registry.register(_BadSchemaPlugin())


class TestDeterministicSchemaValidation:
    def test_validation_with_jsonschema_installed(self) -> None:
        """When jsonschema is available, valid schemas pass and invalid ones fail."""
        from beep.plugins.registry_support import validate_tool_schema

        class _ValidSchemaTool(BaseTool):
            @property
            def name(self) -> str:
                return "valid_schema_tool"

            @property
            def description(self) -> str:
                return "test"

            @property
            def parameters(self) -> dict[str, Any]:
                return {"value": {"type": "string", "description": "A value"}}

            async def execute(self, **kwargs: Any) -> Any:
                from beep.agent.tools.base import ToolResult

                return ToolResult(success=True, output="ok")

        class _InvalidSchemaTool(BaseTool):
            @property
            def name(self) -> str:
                return "invalid_schema_tool"

            @property
            def description(self) -> str:
                return "test"

            @property
            def parameters(self) -> dict[str, Any]:
                return {"value": {"type": 42}}

            async def execute(self, **kwargs: Any) -> Any:
                from beep.agent.tools.base import ToolResult

                return ToolResult(success=True, output="ok")

        assert validate_tool_schema(_ValidSchemaTool()) is True
        assert validate_tool_schema(_InvalidSchemaTool()) is False

    def test_bad_plugin_rejected_with_error(self) -> None:
        """Plugin with invalid tool schemas produces a load error."""
        registry = PluginRegistry()
        registry.register(_BadSchemaPlugin())
        assert len(registry.get_tools()) == 0
        errors = registry.get_load_errors()
        assert len(errors) >= 1
        assert any("bad_schema_tool" in e for e in errors)


# ---------------------------------------------------------------------------
# TestMCPImportGuard
# ---------------------------------------------------------------------------


class TestMCPImportGuard:
    def test_build_agent_tools_survives_mcp_import_error(self) -> None:
        """When MCPClient cannot be imported, build_agent_tools still returns tools."""
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            runtime = _make_runtime(wp)

            with patch.dict(sys.modules, {"beep.mcp.client": None}):
                tools = build_agent_tools(
                    workspace_root=wp,
                    plugin_runtime=runtime,
                    mcp_enabled=True,
                    mcp_servers=[MagicMock()],
                )
            # Should still return the default tools
            assert len(tools) > 0


# ---------------------------------------------------------------------------
# TestCategoryFilter
# ---------------------------------------------------------------------------


class TestCategoryFilter:
    def test_no_filter_returns_all(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            runtime = _make_runtime(wp)
            all_tools = build_agent_tools(
                workspace_root=wp,
                plugin_runtime=runtime,
            )
            filtered = build_agent_tools(
                workspace_root=wp,
                plugin_runtime=runtime,
                categories=None,
            )
            assert len(all_tools) == len(filtered)

    def test_filter_file_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            runtime = _make_runtime(wp)
            tools = build_agent_tools(
                workspace_root=wp,
                plugin_runtime=runtime,
                categories=["file"],
            )
            assert len(tools) > 0
            for t in tools:
                assert t.category == "file"

    def test_filter_exec_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            runtime = _make_runtime(wp)
            tools = build_agent_tools(
                workspace_root=wp,
                plugin_runtime=runtime,
                categories=["exec"],
            )
            for t in tools:
                assert t.category == "exec"

    def test_filter_unknown_category_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            runtime = _make_runtime(wp)
            tools = build_agent_tools(
                workspace_root=wp,
                plugin_runtime=runtime,
                categories=["nonexistent_category_xyz"],
            )
            assert tools == []


# ---------------------------------------------------------------------------
# TestBaseToolCategory
# ---------------------------------------------------------------------------


class TestBaseToolCategory:
    def test_file_read_category(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = FileReadTool(workspace_root=Path(td))
            assert tool.category == "file"

    def test_search_category(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = SearchTool(workspace_root=Path(td))
            assert tool.category == "search"

    def test_shell_category(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = ShellTool(workspace_root=Path(td))
            assert tool.category == "exec"

    def test_custom_fake_tool_category(self) -> None:
        tool = _FakeTool("my_file_tool", category="file")
        assert tool.category == "file"


# ---------------------------------------------------------------------------
# TestPluginDiscoveryPermissionError
# ---------------------------------------------------------------------------


class TestPluginDiscoveryPermissionError:
    def test_permission_error_does_not_crash_runtime(self) -> None:
        """PermissionError from a discovery path should be logged, not raised."""
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            with patch(
                "beep.plugins.registry.PluginRegistry.load_from_directory",
                side_effect=PermissionError("no access"),
            ):
                # load_runtime_plugins catches PermissionError per path
                runtime = load_runtime_plugins(wp)
            # Should complete without raising
            assert runtime.registry is not None

    def test_runtime_loads_successfully_without_plugin_dirs(self) -> None:
        """PluginRuntime must initialise even when no plugin directories exist."""
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            runtime = load_runtime_plugins(wp)
            assert runtime.registry is not None


# ---------------------------------------------------------------------------
# TestWorkspaceRootPassthrough
# ---------------------------------------------------------------------------


class TestWorkspaceRootPassthrough:
    def test_workspace_root_passed_to_plugin(self) -> None:
        """PluginRegistry.get_tools(workspace_root) calls get_tools_for_workspace."""
        plugin = _WorkspaceAwarePlugin()
        registry = PluginRegistry()
        registry.register(plugin)

        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            tools = registry.get_tools(workspace_root=wp)
            assert plugin.received_workspace_root == wp
            assert len(tools) == 1

    def test_workspace_root_none_by_default(self) -> None:
        """get_tools() with no args passes None as workspace_root."""
        plugin = _WorkspaceAwarePlugin()
        registry = PluginRegistry()
        registry.register(plugin)
        registry.get_tools()
        assert plugin.received_workspace_root is None

    def test_build_agent_tools_passes_workspace_root_to_registry(self) -> None:
        """build_agent_tools passes workspace_root into registry.get_tools()."""
        plugin = _WorkspaceAwarePlugin()
        registry = PluginRegistry()
        registry.register(plugin)

        with tempfile.TemporaryDirectory() as td:
            wp = Path(td)
            from beep.plugins.runtime import PluginRuntime

            runtime = PluginRuntime(registry=registry, searched_paths=[], loaded_count=0)
            build_agent_tools(workspace_root=wp, plugin_runtime=runtime)
            assert plugin.received_workspace_root == wp


# ---------------------------------------------------------------------------
# TestMcpToolsCommand
# ---------------------------------------------------------------------------


class TestMcpToolsCommand:
    @pytest.mark.asyncio
    async def test_mcp_status_with_session_runtime(self) -> None:
        """When session-owned MCP runtime exists, /mcp status renders without error."""
        from beep.chat.commands.mcp import McpCommand
        from beep.chat.session_runtime_state import SessionMcpRuntimeState
        from beep.mcp.client import MCPClient
        from beep.mcp.discovery import ResolvedMcpConfiguration

        client = MCPClient()
        runtime = SessionMcpRuntimeState(
            resolution=ResolvedMcpConfiguration(enabled=True, servers=[], sources={}, errors=[]),
            client=client,
        )
        cmd = McpCommand()
        await cmd.execute("status", {"mcp_runtime": runtime})

    @pytest.mark.asyncio
    async def test_mcp_tools_no_client(self, capsys) -> None:
        """When mcp_client is not in context, /mcp tools prints a notice."""
        from beep.chat.commands.mcp import McpCommand

        cmd = McpCommand()
        await cmd.execute("tools", {})
        # rich writes to its own Console; we just check no exception raised

    @pytest.mark.asyncio
    async def test_mcp_tools_empty_client(self) -> None:
        """When MCPClient has no tools, command completes without error."""
        from beep.chat.commands.mcp import McpCommand
        from beep.mcp.client import MCPClient

        client = MCPClient()
        cmd = McpCommand()
        await cmd.execute("tools", {"mcp_client": client})

    @pytest.mark.asyncio
    async def test_mcp_tools_with_tools(self) -> None:
        """When MCPClient has tools, /mcp tools renders a table without error."""
        from beep.chat.commands.mcp import McpCommand
        from beep.mcp.client import MCPClient, MCPTool

        client = MCPClient()
        client.add_tool(
            MCPTool(
                name="test_tool",
                description="A test tool",
                parameters={},
                read_only_safe=True,
                requires_human_approval=False,
                server_name="test_server",
                server_command="python",
                server_args=[],
                server_env={},
            )
        )
        cmd = McpCommand()
        await cmd.execute("tools", {"mcp_client": client})

    @pytest.mark.asyncio
    async def test_mcp_tools_show_policy_columns(self, capsys) -> None:
        """/mcp tools exposes read-only and approval policy for each MCP tool."""
        from beep.chat.commands.mcp import McpCommand
        from beep.mcp.client import MCPClient, MCPTool

        client = MCPClient()
        client.add_tool(
            MCPTool(
                name="test_tool",
                description="A test tool",
                parameters={},
                read_only_safe=True,
                requires_human_approval=False,
                server_name="test_server",
                server_command="python",
                server_args=[],
                server_env={},
            )
        )

        cmd = McpCommand()
        await cmd.execute("tools", {"mcp_client": client})

        out = capsys.readouterr().out
        assert "Read-only" in out
        assert "Approval" in out
        assert "Yes" in out
        assert "Not required" in out

    @pytest.mark.asyncio
    async def test_mcp_servers_subcommand(self) -> None:
        """'/mcp servers' lists registered server names."""
        from beep.chat.commands.mcp import McpCommand
        from beep.mcp.client import MCPClient, MCPServer

        client = MCPClient()
        client.register_server(
            MCPServer(name="srv1", command="bin", args=[], env={}, connected=True)
        )
        cmd = McpCommand()
        await cmd.execute("servers", {"mcp_client": client})

    @pytest.mark.asyncio
    async def test_mcp_default_subcommand_is_tools(self) -> None:
        """Calling '/mcp' with no args defaults to tools subcommand."""
        from beep.chat.commands.mcp import McpCommand

        cmd = McpCommand()
        # Should not raise
        await cmd.execute("", {})

    @pytest.mark.asyncio
    async def test_mcp_tools_report_client_error(self, capsys) -> None:
        """When session-owned MCP runtime has a client error, /mcp tools shows it."""
        from beep.chat.commands.mcp import McpCommand
        from beep.chat.session_runtime_state import SessionMcpRuntimeState

        cmd = McpCommand()
        await cmd.execute("tools", {"mcp_runtime": SessionMcpRuntimeState(client_error="mcp boom")})
        assert "mcp boom" in capsys.readouterr().out
