"""CLI tests for the agent command group."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from beep.cli import app
from beep.config import BeepConfig
from beep.permissions.manager import SandboxMode
from beep.runtime.workspace_intelligence import WorkspaceIntelligenceStatusReport, WorkspaceIntelligenceStatusRow


def test_agent_group_routes_freeform_goal_to_agent_cmd() -> None:
    runner = CliRunner()
    with patch("beep.cli.agent_cmd") as agent_cmd_mock:
        result = runner.invoke(app, ["agent", "fix", "failing", "tests", "--no-plugins"])
    assert result.exit_code == 0
    agent_cmd_mock.assert_called_once_with(
        "fix failing tests",
        max_steps=20,
        auto_approve=False,
        sandbox=SandboxMode.WORKSPACE_WRITE,
        model=None,
        no_plugins=True,
        response_json=False,
        response_schema=None,
        input_file=None,
        input_image=None,
    )


def test_agent_status_subcommand_is_available() -> None:
    runner = CliRunner()
    payload = {
        "status": "not_created",
        "compatibility_status": "stale",
        "compatibility_reason": "Managed agent environment has no recorded compatibility stamp.",
        "repair_action": "setup",
        "repair_command": "beep agent setup",
        "repair_reason": "Managed agent environment does not exist yet.",
        "env_path": "C:/tmp/agents_env",
        "python_exe": "C:/tmp/agents_env/Scripts/python.exe",
        "size_bytes": 0,
        "missing": ["langgraph"],
        "last_error": None,
        "packages": {
            "langgraph": {
                "name": "LangGraph",
                "required": True,
                "installed": False,
                "pip_name": "langgraph>=0.4",
            }
        },
    }
    manager = MagicMock()
    manager.status.return_value = payload
    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(server_url="http://localhost:5000", api_token="token"),
    ):
        with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
            result = runner.invoke(app, ["agent", "status"])
    assert result.exit_code == 0
    assert "Agent Runtime Environment" in (result.stdout or "")
    assert "Agent Provider" in (result.stdout or "")
    assert "Provider Guidance" in (result.stdout or "")
    assert "Provider Capabilities" in (result.stdout or "")
    assert "Compatibility" in (result.stdout or "")
    assert "beep agent setup" in (result.stdout or "")
    assert "stale" in (result.stdout or "")
    assert "LangGraph" in (result.stdout or "")
    assert "Workspace Intelligence" in (result.stdout or "")
    assert "Workspace Intelligence Capabilities" in (result.stdout or "")
    assert "Tool Calling" in (result.stdout or "")
    assert "Agent environment not ready" in (result.stdout or "")


def test_agent_status_uses_provider_default_base_url_without_override() -> None:
    runner = CliRunner()
    payload = {
        "status": "not_created",
        "compatibility_status": "stale",
        "compatibility_reason": "Managed agent environment has no recorded compatibility stamp.",
        "repair_action": "setup",
        "repair_command": "beep agent setup",
        "repair_reason": "Managed agent environment does not exist yet.",
        "env_path": "C:/tmp/agents_env",
        "python_exe": "C:/tmp/agents_env/Scripts/python.exe",
        "size_bytes": 0,
        "missing": ["langgraph"],
        "last_error": None,
        "packages": {},
    }
    manager = MagicMock()
    manager.status.return_value = payload
    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(
            agent_backend="anthropic",
            agent_api_key="anthropic-token",
            agent_model="claude-sonnet-4-20250514",
            agent_thinking_budget_tokens=2048,
        ),
    ):
        with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
            with patch("beep.commands.agent._load_plugin_registry_for_agent_status", return_value=None):
                result = runner.invoke(app, ["agent", "status"])

    assert result.exit_code == 0
    assert "Anthropic" in (result.stdout or "")
    assert "https://api.anthropic.com" in (result.stdout or "")
    assert "Thinking Budget" in (result.stdout or "")
    assert "2048" in (result.stdout or "")


def test_agent_status_uses_openrouter_default_base_url_with_path_prefix() -> None:
    runner = CliRunner()
    payload = {
        "status": "not_created",
        "compatibility_status": "stale",
        "compatibility_reason": "Managed agent environment has no recorded compatibility stamp.",
        "repair_action": "setup",
        "repair_command": "beep agent setup",
        "repair_reason": "Managed agent environment does not exist yet.",
        "env_path": "C:/tmp/agents_env",
        "python_exe": "C:/tmp/agents_env/Scripts/python.exe",
        "size_bytes": 0,
        "missing": ["langgraph"],
        "last_error": None,
        "packages": {},
    }
    manager = MagicMock()
    manager.status.return_value = payload
    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(
            agent_backend="openrouter",
            agent_api_key="openrouter-token",
            agent_model="anthropic/claude-sonnet-4",
            agent_reasoning_effort="high",
            agent_parallel_tool_calls=False,
        ),
    ):
        with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
            with patch("beep.commands.agent._load_plugin_registry_for_agent_status", return_value=None):
                result = runner.invoke(app, ["agent", "status"])

    assert result.exit_code == 0
    assert "OpenRouter" in (result.stdout or "")
    assert "https://openrouter.ai/api" in (result.stdout or "")
    assert "Reasoning Effort" in (result.stdout or "")
    assert "high" in (result.stdout or "")
    assert "Parallel Tool Calls" in (result.stdout or "")
    assert "Disabled" in (result.stdout or "")


def test_agent_reinstall_runtime_rebuilds_managed_environment() -> None:
    runner = CliRunner()
    payload = {
        "status": "ready",
        "compatibility_status": "current",
        "compatibility_reason": "Managed agent environment matches the current CLI compatibility stamp.",
        "repair_action": "none",
        "repair_command": None,
        "repair_reason": "Managed agent runtime is current.",
        "env_path": "C:/tmp/agents_env",
        "python_exe": "C:/tmp/agents_env/Scripts/python.exe",
        "size_bytes": 1024,
        "missing": [],
        "last_error": None,
        "packages": {},
    }
    manager = MagicMock()
    manager.reinstall_environment.return_value = payload

    with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
        result = runner.invoke(app, ["agent", "reinstall", "runtime"])

    assert result.exit_code == 0
    manager.reinstall_environment.assert_called_once()
    assert "Reinstalled managed agent runtime." in (result.stdout or "")


def test_agent_setup_surfaces_runtime_reinstall_guidance_for_partial_install() -> None:
    runner = CliRunner()
    manager = MagicMock()
    manager.install_required_packages.side_effect = RuntimeError(
        'Previous managed runtime setup did not complete cleanly; rebuild the managed runtime from scratch. Run "beep agent reinstall runtime".'
    )

    with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
        result = runner.invoke(app, ["agent", "setup"])

    assert result.exit_code == 1
    normalized = " ".join((result.stdout or "").split())
    assert "beep agent reinstall runtime" in normalized


def test_agent_status_renders_semble_runtime_report_when_environment_ready() -> None:
    runner = CliRunner()
    payload = {
        "status": "ready",
        "env_path": "C:/tmp/agents_env",
        "python_exe": "C:/tmp/agents_env/Scripts/python.exe",
        "size_bytes": 1024,
        "missing": [],
        "last_error": None,
        "packages": {
            "semble": {
                "name": "Semble",
                "required": True,
                "installed": True,
                "pip_name": "semble>=0.1.1",
            }
        },
    }
    manager = MagicMock()
    manager.status.return_value = payload
    manager.inject_into_sys_path.return_value = None
    adapter = MagicMock()
    adapter.availability_report.return_value = {
        "available": True,
        "workspace_root": "C:/workspace/project",
        "cached": True,
        "cached_root": "C:/workspace/project",
        "error": None,
        "stats": {
            "indexed_files": 12,
            "total_chunks": 48,
            "languages": {"python": 40, "json": 8},
        },
    }
    runtime = MagicMock(semantic_search_adapter=adapter)
    runtime.plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_reports=lambda workspace_root: [
                WorkspaceIntelligenceStatusReport(
                    title="Workspace Intelligence: Semble",
                    rows=(
                        WorkspaceIntelligenceStatusRow("Semble Available", "Yes"),
                        WorkspaceIntelligenceStatusRow("Workspace", "C:/workspace/project"),
                        WorkspaceIntelligenceStatusRow("Index Cached", "Yes"),
                        WorkspaceIntelligenceStatusRow("Cached Root", "C:/workspace/project"),
                        WorkspaceIntelligenceStatusRow("Last Error", "None"),
                        WorkspaceIntelligenceStatusRow("Indexed Files", "12"),
                        WorkspaceIntelligenceStatusRow("Total Chunks", "48"),
                        WorkspaceIntelligenceStatusRow("Languages", "python=40, json=8"),
                    ),
                )
            ]
        )
    )
    runtime.workspace_intelligence_capabilities = MagicMock(
        semantic_search=MagicMock(
            semantic_search=MagicMock(exists=True, notes="Semble semantic retrieval available."),
            find_related=MagicMock(exists=True, notes="Semble related-code retrieval available."),
            local_indexing=MagicMock(exists=True, notes="Indexes the local workspace."),
            remote_git_indexing=MagicMock(exists=False, notes="Remote git indexing unavailable."),
            hybrid_mode=MagicMock(exists=True, notes="Hybrid mode available."),
            semantic_mode=MagicMock(exists=True, notes="Semantic mode available."),
            bm25_mode=MagicMock(exists=True, notes="BM25 mode available."),
            language_filters=MagicMock(exists=True, notes="Language filters supported."),
            path_filters=MagicMock(exists=True, notes="Path filters supported."),
            index_stats=MagicMock(exists=True, notes="Cached index stats available."),
        ),
        lsp=MagicMock(
            diagnostics=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            hover=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            definition=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            references=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            rename=MagicMock(exists=False, notes="Rename unavailable."),
            workspace_symbols=MagicMock(exists=False, notes="Workspace symbols unavailable."),
            code_actions=MagicMock(exists=False, notes="Code actions unavailable."),
            formatting=MagicMock(exists=False, notes="Formatting unavailable."),
        ),
    )

    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(
            agent_backend="openai-compatible",
            agent_base_url="http://provider.test",
            agent_api_key="provider-token",
            agent_model="model-x",
        ),
    ):
        with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
            with patch("beep.commands.agent.find_workspace_root", return_value=Path("C:/workspace")):
                with patch("beep.commands.agent.get_workspace_runtime", return_value=runtime):
                    result = runner.invoke(app, ["agent", "status"])

    assert result.exit_code == 0
    assert "OpenAI-Compatible" in (result.stdout or "")
    assert "Default Base URL" in (result.stdout or "")
    assert "Semble Available" in (result.stdout or "")
    assert "Indexed Files" in (result.stdout or "")
    assert "12" in (result.stdout or "")
    assert "python=40" in (result.stdout or "")
    assert "Semantic Search" in (result.stdout or "")
    assert "Remote Git Indexing" in (result.stdout or "")
    assert "LSP Diagnostics" in (result.stdout or "")
    assert "LSP Workspace Symbols" in (result.stdout or "")


def test_agent_status_prefers_workspace_intelligence_registry_reports() -> None:
    runner = CliRunner()
    payload = {
        "status": "ready",
        "env_path": "C:/tmp/agents_env",
        "python_exe": "C:/tmp/agents_env/Scripts/python.exe",
        "size_bytes": 1024,
        "missing": [],
        "last_error": None,
        "packages": {},
    }
    manager = MagicMock()
    manager.status.return_value = payload
    manager.inject_into_sys_path.return_value = None
    adapter = MagicMock()
    adapter.availability_report.side_effect = AssertionError("adapter report should not be used")
    runtime = MagicMock(semantic_search_adapter=adapter)
    runtime.plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_workspace_intelligence_reports=lambda workspace_root: [
                WorkspaceIntelligenceStatusReport(
                    title="Workspace Intelligence: Python LSP",
                    rows=(
                        WorkspaceIntelligenceStatusRow("Workspace", "C:/workspace/from-plugin"),
                        WorkspaceIntelligenceStatusRow("Diagnostics", "Ready"),
                        WorkspaceIntelligenceStatusRow("Indexed Files", "3"),
                    ),
                )
            ]
        )
    )
    runtime.workspace_intelligence_capabilities = MagicMock(
        semantic_search=MagicMock(
            semantic_search=MagicMock(exists=True, notes="Semble semantic retrieval available."),
            find_related=MagicMock(exists=True, notes="Semble related-code retrieval available."),
            local_indexing=MagicMock(exists=True, notes="Indexes the local workspace."),
            remote_git_indexing=MagicMock(exists=False, notes="Remote git indexing unavailable."),
            hybrid_mode=MagicMock(exists=True, notes="Hybrid mode available."),
            semantic_mode=MagicMock(exists=True, notes="Semantic mode available."),
            bm25_mode=MagicMock(exists=True, notes="BM25 mode available."),
            language_filters=MagicMock(exists=True, notes="Language filters supported."),
            path_filters=MagicMock(exists=True, notes="Path filters supported."),
            index_stats=MagicMock(exists=True, notes="Cached index stats available."),
        ),
        lsp=MagicMock(
            diagnostics=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            hover=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            definition=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            references=MagicMock(exists=False, notes="LSP workspace intelligence is not implemented yet."),
            rename=MagicMock(exists=False, notes="Rename unavailable."),
            workspace_symbols=MagicMock(exists=True, notes="Workspace symbols available from plugin."),
            code_actions=MagicMock(exists=False, notes="Code actions unavailable."),
            formatting=MagicMock(exists=False, notes="Formatting unavailable."),
        ),
    )

    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(server_url="http://localhost:5000", api_token="token"),
    ):
        with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
            with patch("beep.commands.agent.find_workspace_root", return_value=Path("C:/workspace")):
                with patch("beep.commands.agent.get_workspace_runtime", return_value=runtime):
                    result = runner.invoke(app, ["agent", "status"])

    assert result.exit_code == 0
    assert "Workspace Intelligence: Python LSP" in (result.stdout or "")
    assert "C:/workspace/from-plugin" in (result.stdout or "")
    assert "3" in (result.stdout or "")
    assert "LSP Workspace Symbols" in (result.stdout or "")


def test_agent_status_uses_runtime_plugin_provider() -> None:
    runner = CliRunner()
    payload = {
        "status": "not_created",
        "env_path": "C:/tmp/agents_env",
        "python_exe": "C:/tmp/agents_env/Scripts/python.exe",
        "size_bytes": 0,
        "missing": ["langgraph"],
        "last_error": None,
        "packages": {},
    }
    manager = MagicMock()
    manager.status.return_value = payload
    provider = SimpleNamespace(
        is_configured=lambda config: True,
        describe=lambda config: SimpleNamespace(
            key="custom-provider",
            display_name="Custom Provider",
            capabilities=SimpleNamespace(
                chat_completion=SimpleNamespace(exists=True, notes="Chat available."),
                tool_calling=SimpleNamespace(exists=True, notes="Tool calling available."),
                streaming=SimpleNamespace(exists=False, notes="Streaming unavailable."),
                structured_output=SimpleNamespace(exists=False, notes="Structured output unavailable."),
                vision=SimpleNamespace(exists=False, notes="Vision unavailable."),
                embeddings=SimpleNamespace(exists=False, notes="Embeddings unavailable."),
                local_model_runtime=SimpleNamespace(exists=False, notes="No local runtime."),
            ),
        ),
    )
    plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(get_backend_provider=lambda key: provider if key == "custom-provider" else None)
    )

    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(agent_backend="custom-provider"),
    ):
        with patch("beep.commands.agent.load_runtime_plugins", return_value=plugin_runtime):
            with patch("beep.commands.agent.AgentEnvironmentManager", return_value=manager):
                result = runner.invoke(app, ["agent", "status"])

    assert result.exit_code == 0
    assert "Custom Provider" in (result.stdout or "")
    assert "custom-provider" in (result.stdout or "")


def test_agent_providers_lists_builtin_provider_guidance() -> None:
    runner = CliRunner()
    plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(
            list_backend_providers=lambda: [],
            get_backend_provider=lambda key: None,
        )
    )

    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(agent_backend="lm-studio", agent_model="qwen-coder"),
    ):
        with patch("beep.commands.agent.load_runtime_plugins", return_value=plugin_runtime):
            with patch("beep.commands.agent.find_workspace_root", return_value=MagicMock()):
                result = runner.invoke(app, ["agent", "providers"])

    assert result.exit_code == 0
    assert "Agent Providers" in (result.stdout or "")
    assert "beep" in (result.stdout or "")
    assert "Beep.AI.Server" in (result.stdout or "")
    assert "anthropic" in (result.stdout or "")
    assert "Anthropic" in (result.stdout or "")
    assert "openai" in (result.stdout or "")
    assert "OpenAI" in (result.stdout or "")
    assert "openrouter" in (result.stdout or "")
    assert "OpenRouter" in (result.stdout or "")
    assert "lm-studio" in (result.stdout or "")
    assert "LM Studio" in (result.stdout or "")
    assert "ollama" in (result.stdout or "")
    assert "http://localhost:1234" in (result.stdout or "")


def test_agent_providers_lists_runtime_plugin_provider() -> None:
    runner = CliRunner()
    provider = SimpleNamespace(
        is_configured=lambda config: True,
        describe=lambda config: SimpleNamespace(
            key="custom-provider",
            display_name="Custom Provider",
            capabilities=SimpleNamespace(local_model_runtime=SimpleNamespace(exists=False)),
        ),
        source_label=lambda: "plugin",
        requires_api_key=lambda: False,
        requires_model=lambda: True,
        default_base_url=lambda: None,
        configuration_notes=lambda config: ("Set agent_model before use.",),
    )
    plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(
            list_backend_providers=lambda: ["custom-provider"],
            get_backend_provider=lambda key: provider if key == "custom-provider" else None,
        )
    )

    with patch(
        "beep.commands.agent.load_config",
        return_value=BeepConfig(agent_backend="custom-provider", agent_model="model-x"),
    ):
        with patch("beep.commands.agent.load_runtime_plugins", return_value=plugin_runtime):
            with patch("beep.commands.agent.find_workspace_root", return_value=MagicMock()):
                result = runner.invoke(app, ["agent", "providers"])

    assert result.exit_code == 0
    assert "custom-provider" in (result.stdout or "")
    assert "Custom Provider" in (result.stdout or "")
    assert "plugin" in (result.stdout or "")


def test_agent_configure_subcommand_routes_provider_to_setup_wizard() -> None:
    runner = CliRunner()
    with patch("beep.cli.run_agent_provider_setup_wizard") as configure_mock:
        result = runner.invoke(app, ["agent", "configure", "lm-studio"])

    assert result.exit_code == 0
    configure_mock.assert_called_once_with("lm-studio")


def test_agent_resume_subcommand_routes_thread_to_resume_cmd() -> None:
    runner = CliRunner()
    with patch("beep.cli.agent_resume_cmd") as resume_cmd_mock:
        result = runner.invoke(app, ["agent", "resume", "thread-9", "--no-plugins"])
    assert result.exit_code == 0
    resume_cmd_mock.assert_called_once_with(
        "thread-9",
        max_steps=20,
        auto_approve=False,
        sandbox=SandboxMode.WORKSPACE_WRITE,
        model=None,
        no_plugins=True,
        response_json=False,
        response_schema=None,
        input_file=None,
        input_image=None,
    )