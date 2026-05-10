"""Tests for plugin system."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from beep.agent.provider_plugin_base import OpenAICompatibleProviderPluginBase
from beep.agent.provider_capabilities import ProviderCapabilities, ProviderDescriptor
from beep.config import BeepConfig
from beep.agent.tools.base import BaseTool, ToolResult
from beep.plugins.registry import (
    BackendProviderPlugin,
    CommandPlugin,
    ContextPlugin,
    PluginInfo,
    PluginRegistry,
    ToolPlugin,
    WorkspaceIntelligencePlugin,
)
from beep.runtime.capabilities import CapabilityFlag
from beep.runtime.workspace_intelligence import LSPCapabilities, SemanticSearchCapabilities, WorkspaceIntelligenceCapabilities
from beep.runtime.workspace_intelligence import (
    LSPCapabilities,
    SemanticSearchCapabilities,
    WorkspaceIntelligenceCapabilities,
    WorkspaceIntelligenceStatusReport,
    WorkspaceIntelligenceStatusRow,
)
from beep.plugins.runtime import load_runtime_plugins


class DummyTool(BaseTool):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "A dummy tool"

    @property
    def parameters(self) -> dict:
        return {}

    async def execute(self) -> ToolResult:
        return ToolResult(success=True, output="dummy ran")


class DummyToolPlugin(ToolPlugin):
    info = PluginInfo(
        name="dummy-tool", version="1.0.0", description="Test tool plugin"
    )

    def activate(self) -> None:
        pass

    def get_tools(self) -> list[BaseTool]:
        return [DummyTool()]


class DummyCommandPlugin(CommandPlugin):
    info = PluginInfo(
        name="dummy-cmd", version="1.0.0", description="Test command plugin"
    )

    def activate(self) -> None:
        pass

    def get_commands(self) -> dict[str, str]:
        return {"dummy": "Run dummy command"}

    async def handle_command(self, command: str, args: str) -> str | None:
        if command == "dummy":
            return f"Dummy response: {args}"
        return None


class DummyContextPlugin(ContextPlugin):
    info = PluginInfo(
        name="dummy-ctx", version="1.0.0", description="Test context plugin"
    )

    def activate(self) -> None:
        pass

    def get_context(self) -> str:
        return "Extra context from plugin"


class DummyBackendProviderPlugin(BackendProviderPlugin):
    info = PluginInfo(
        name="dummy-backend", version="1.0.0", description="Test backend provider plugin"
    )

    def activate(self) -> None:
        pass

    def provider_key(self) -> str:
        return "dummy-backend"

    def is_configured(self, config: object) -> bool:
        return True

    def describe(self, config: object) -> ProviderDescriptor:
        return ProviderDescriptor(
            key="dummy-backend",
            display_name="Dummy Backend",
            capabilities=ProviderCapabilities(
                chat_completion=CapabilityFlag(True, "Chat available."),
                tool_calling=CapabilityFlag(True, "Tool calling available."),
                streaming=CapabilityFlag(False, "Streaming unavailable."),
                structured_output=CapabilityFlag(False, "Structured output unavailable."),
                vision=CapabilityFlag(False, "Vision unavailable."),
                embeddings=CapabilityFlag(False, "Embeddings unavailable."),
                local_model_runtime=CapabilityFlag(False, "No local runtime."),
            ),
        )

    def build_backend(self, config: object, *, client: object = None, coding_assistant: dict | None = None) -> object:
        return object()


class DummyWorkspaceIntelligencePlugin(WorkspaceIntelligencePlugin):
    info = PluginInfo(
        name="dummy-workspace-intelligence",
        version="1.0.0",
        description="Test workspace intelligence plugin",
    )

    def activate(self) -> None:
        pass

    def capabilities(self, *, workspace_root: Path) -> WorkspaceIntelligenceCapabilities:
        del workspace_root
        return WorkspaceIntelligenceCapabilities(
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
                hover=CapabilityFlag(False, "Plugin hover unavailable."),
                definition=CapabilityFlag(False, "Plugin definition unavailable."),
                references=CapabilityFlag(False, "Plugin references unavailable."),
                rename=CapabilityFlag(False, "Plugin rename unavailable."),
                workspace_symbols=CapabilityFlag(False, "Plugin workspace symbols unavailable."),
                code_actions=CapabilityFlag(False, "Plugin code actions unavailable."),
                formatting=CapabilityFlag(False, "Plugin formatting unavailable."),
            ),
        )

    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]:
        del workspace_root
        return [DummyTool()]

    def get_semantic_search_adapter(self, workspace_root: Path) -> object | None:
        return SimpleNamespace(
            workspace_root=workspace_root,
            availability_report=lambda: {"available": True, "error": None},
        )
    def get_status_report(self, workspace_root: Path) -> WorkspaceIntelligenceStatusReport | None:
        return WorkspaceIntelligenceStatusReport(
            title="Workspace Intelligence: Dummy",
            rows=(
                WorkspaceIntelligenceStatusRow("Workspace", str(workspace_root)),
                WorkspaceIntelligenceStatusRow("Available", "Yes"),
            ),
        )


class DummyOpenAICompatibleProviderPlugin(OpenAICompatibleProviderPluginBase):
    info = PluginInfo(
        name="dummy-openai-compatible-plugin",
        version="1.0.0",
        description="Test helper-based backend provider plugin",
    )
    provider_key_value = "dummy-openai-compatible"
    display_name = "Dummy OpenAI-Compatible"
    default_base_url_value = "https://dummy-provider.example/api"

    def activate(self) -> None:
        pass

    def configuration_notes(self, config: object) -> tuple[str, ...]:
        del config
        return ("Set agent_model before use.",)


class TestPluginRegistry:
    def test_register_tool_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = DummyToolPlugin()
        registry.register(plugin)
        tools = registry.get_tools()
        assert len(tools) == 1
        assert tools[0].name == "dummy"

    def test_register_command_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = DummyCommandPlugin()
        registry.register(plugin)
        cmds = registry.get_command_descriptions()
        assert "dummy" in cmds
        assert cmds["dummy"] == "Run dummy command"

    def test_register_context_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = DummyContextPlugin()
        registry.register(plugin)
        ctx = registry.get_context()
        assert "Extra context" in ctx

    def test_register_backend_provider_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = DummyBackendProviderPlugin()
        registry.register(plugin)
        assert registry.get_backend_provider("dummy-backend") is plugin
        assert registry.list_backend_providers() == ["dummy-backend"]

    def test_register_openai_compatible_provider_plugin_helper(self) -> None:
        registry = PluginRegistry()
        plugin = DummyOpenAICompatibleProviderPlugin()

        registry.register(plugin)

        assert registry.get_backend_provider("dummy-openai-compatible") is plugin
        assert "dummy-openai-compatible" in registry.list_backend_providers()

    def test_register_workspace_intelligence_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = DummyWorkspaceIntelligencePlugin()
        registry.register(plugin)

        capabilities = registry.get_workspace_intelligence_capabilities(Path.cwd())
        tools = registry.get_workspace_intelligence_tools(Path.cwd())
        adapter = registry.get_semantic_search_adapter(Path.cwd())
        reports = registry.get_workspace_intelligence_reports(Path.cwd())

        assert len(capabilities) == 1
        assert capabilities[0].lsp.diagnostics.exists is True
        assert len(tools) == 1
        assert tools[0].name == "dummy"
        assert adapter is not None
        assert adapter.availability_report()["available"] is True
        assert len(reports) == 1
        assert reports[0].title == "Workspace Intelligence: Dummy"

    def test_unregister_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = DummyToolPlugin()
        registry.register(plugin)
        assert len(registry.get_tools()) == 1

        registry.unregister("dummy-tool")
        assert "dummy-tool" not in registry._plugins

    def test_list_plugins(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyToolPlugin())
        registry.register(DummyCommandPlugin())
        plugins = registry.list_plugins()
        assert len(plugins) == 2
        names = {p["name"] for p in plugins}
        assert "dummy-tool" in names
        assert "dummy-cmd" in names

    @pytest.mark.asyncio
    async def test_handle_plugin_command(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyCommandPlugin())
        result = await registry.handle_plugin_command("dummy", "test args")
        assert result == "Dummy response: test args"

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self) -> None:
        registry = PluginRegistry()
        result = await registry.handle_plugin_command("unknown", "")
        assert result is None

    def test_load_from_file(self) -> None:
        plugin_code = '''
from beep.plugins.registry import Plugin, PluginInfo, ToolPlugin
from beep.agent.tools.base import BaseTool, ToolResult

class TestTool(BaseTool):
    @property
    def name(self):
        return "test"
    @property
    def description(self):
        return "Test"
    @property
    def parameters(self):
        return {}
    async def execute(self):
        return ToolResult(success=True, output="test")

class TestPlugin(ToolPlugin):
    info = PluginInfo(name="test-plugin")
    def activate(self):
        pass
    def get_tools(self):
        return [TestTool()]
'''
        with tempfile.TemporaryDirectory() as td:
            plugin_file = Path(td) / "test_plugin.py"
            plugin_file.write_text(plugin_code, encoding="utf-8")

            registry = PluginRegistry()
            registry.load_from_file(plugin_file)
            tools = registry.get_tools()
            assert len(tools) == 1
            assert tools[0].name == "test"

    def test_load_from_directory(self) -> None:
        plugin_code = '''
from beep.plugins.registry import Plugin, PluginInfo

class DirPlugin(Plugin):
    info = PluginInfo(name="dir-plugin")
    def activate(self):
        pass
'''
        with tempfile.TemporaryDirectory() as td:
            plugin_file = Path(td) / "my_plugin.py"
            plugin_file.write_text(plugin_code, encoding="utf-8")

            registry = PluginRegistry()
            count = registry.load_from_directory(Path(td))
            assert count == 1
            assert "dir-plugin" in registry._plugins

    def test_load_from_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = PluginRegistry()
            count = registry.load_from_directory(Path(td))
            assert count == 0

    def test_load_from_nonexistent_directory(self) -> None:
        registry = PluginRegistry()
        count = registry.load_from_directory(Path("/nonexistent"))
        assert count == 0

    def test_skip_underscore_files(self) -> None:
        plugin_code = '''
from beep.plugins.registry import Plugin, PluginInfo

class SkipPlugin(Plugin):
    info = PluginInfo(name="skip")
    def activate(self):
        pass
'''
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "__init__.py").write_text(
                plugin_code, encoding="utf-8"
            )

            registry = PluginRegistry()
            count = registry.load_from_directory(Path(td))
            assert count == 0

    def test_combined_plugins(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyToolPlugin())
        registry.register(DummyCommandPlugin())
        registry.register(DummyContextPlugin())
        registry.register(DummyBackendProviderPlugin())
        registry.register(DummyWorkspaceIntelligencePlugin())

        assert len(registry.get_tools()) == 1
        assert len(registry.get_command_descriptions()) == 1
        assert registry.get_context() != ""
        assert len(registry.list_plugins()) == 5

    def test_load_backend_provider_plugin_from_file(self) -> None:
        plugin_code = '''
from beep.agent.provider_capabilities import ProviderCapabilities, ProviderDescriptor
from beep.plugins.registry import BackendProviderPlugin, PluginInfo
from beep.runtime.capabilities import CapabilityFlag

class FileBackendPlugin(BackendProviderPlugin):
    info = PluginInfo(name="file-backend-plugin")
    def activate(self):
        pass
    def provider_key(self):
        return "file-backend"
    def is_configured(self, config):
        return True
    def describe(self, config):
        return ProviderDescriptor(
            key="file-backend",
            display_name="File Backend",
            capabilities=ProviderCapabilities(
                chat_completion=CapabilityFlag(True, "Chat available."),
                tool_calling=CapabilityFlag(True, "Tool calling available."),
                streaming=CapabilityFlag(False, "Streaming unavailable."),
                structured_output=CapabilityFlag(False, "Structured output unavailable."),
                vision=CapabilityFlag(False, "Vision unavailable."),
                embeddings=CapabilityFlag(False, "Embeddings unavailable."),
                local_model_runtime=CapabilityFlag(False, "No local runtime."),
            ),
        )
    def build_backend(self, config, *, client=None, coding_assistant=None):
        return object()
'''
        with tempfile.TemporaryDirectory() as td:
            plugin_file = Path(td) / "backend_plugin.py"
            plugin_file.write_text(plugin_code, encoding="utf-8")

            registry = PluginRegistry()
            registry.load_from_file(plugin_file)
            assert registry.get_backend_provider("file-backend") is not None

    def test_load_openai_compatible_provider_plugin_helper_from_file(self) -> None:
        plugin_code = '''
from beep.agent.provider_plugin_base import OpenAICompatibleProviderPluginBase
from beep.plugins.registry import PluginInfo

class FileOpenAICompatibleProvider(OpenAICompatibleProviderPluginBase):
    info = PluginInfo(name="file-openai-compatible-plugin")
    provider_key_value = "file-openai-compatible"
    display_name = "File OpenAI-Compatible"
    default_base_url_value = "https://example.test/api"

    def activate(self):
        pass
'''
        with tempfile.TemporaryDirectory() as td:
            plugin_file = Path(td) / "openai_compatible_plugin.py"
            plugin_file.write_text(plugin_code, encoding="utf-8")

            registry = PluginRegistry()
            registry.load_from_file(plugin_file)

            provider = registry.get_backend_provider("file-openai-compatible")
            assert provider is not None
            assert provider.default_base_url() == "https://example.test/api"

    @pytest.mark.asyncio
    async def test_openai_compatible_provider_plugin_helper_probe_uses_models_endpoint(self) -> None:
        plugin = DummyOpenAICompatibleProviderPlugin()

        import httpx

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/models"
            return httpx.Response(200, json={"data": [{"id": "dummy-model"}]})

        client = httpx.AsyncClient(
            base_url="https://dummy-provider.example/api/",
            transport=httpx.MockTransport(handler),
        )
        config = BeepConfig(
            agent_backend="dummy-openai-compatible",
            agent_api_key="dummy-token",
            agent_model="dummy-model",
        )

        try:
            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setattr(
                    "beep.agent.provider_plugin_base.httpx.AsyncClient",
                    lambda *args, **kwargs: client,
                )
                result = await plugin.probe_configuration(config)
        finally:
            await client.aclose()

        assert result.supported is True
        assert result.success is True
        assert "dummy-model" in result.message

    def test_load_errors_collected(self) -> None:
        bad_plugin_code = "def this_is_invalid_python("
        with tempfile.TemporaryDirectory() as td:
            plugin_file = Path(td) / "bad_plugin.py"
            plugin_file.write_text(bad_plugin_code, encoding="utf-8")

            registry = PluginRegistry()
            count = registry.load_from_directory(Path(td))

            assert count == 0
            errors = registry.get_load_errors()
            assert len(errors) == 1
            assert "bad_plugin.py" in errors[0]


class TestPluginRuntime:
    def test_load_runtime_plugins_from_workspace_and_env(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            workspace_root = Path(workspace)
            workspace_plugins = workspace_root / ".beep" / "plugins"
            workspace_plugins.mkdir(parents=True)
            workspace_plugins.joinpath("workspace_plugin.py").write_text(
                """
from beep.plugins.registry import Plugin, PluginInfo

class WorkspacePlugin(Plugin):
    info = PluginInfo(name="workspace-plugin")
    def activate(self): ...
""",
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as env_plugins_dir:
                env_path = Path(env_plugins_dir)
                env_path.joinpath("env_plugin.py").write_text(
                    """
from beep.plugins.registry import Plugin, PluginInfo

class EnvPlugin(Plugin):
    info = PluginInfo(name="env-plugin")
    def activate(self): ...
""",
                    encoding="utf-8",
                )
                monkeypatch.setenv("BEEP_PLUGINS_DIR", str(env_path))

                runtime = load_runtime_plugins(workspace_root)

                names = {p["name"] for p in runtime.registry.list_plugins()}
                assert "workspace-plugin" in names
                assert "env-plugin" in names
                assert runtime.loaded_count == 2

    def test_load_runtime_plugins_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace_root = Path(td)
            runtime = load_runtime_plugins(workspace_root, enabled=False)
        assert runtime.loaded_count == 0
        assert runtime.registry.list_plugins() == []
