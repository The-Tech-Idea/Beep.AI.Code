"""Tests for run_agent orchestration."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.agent.bundle_contract import PortableAgentBundleManifest
from beep.agent.loop import resume_agent, run_agent
from beep.agent.provider_capabilities import ProviderCapabilities, ProviderDescriptor
from beep.config import BeepConfig, MCPServerConfig, MCPToolConfig
from beep.permissions.manager import SandboxMode
from beep.runtime.capabilities import CapabilityFlag
from beep.runtime.workspace_intelligence import build_workspace_intelligence_capabilities


def _runtime() -> SimpleNamespace:
    registry = SimpleNamespace(get_tools=lambda workspace_root=None: [])
    return SimpleNamespace(
        plugin_runtime=SimpleNamespace(registry=registry),
        semantic_search_adapter=object(),
        workspace_intelligence_capabilities=build_workspace_intelligence_capabilities(
            {"available": True, "error": None}
        ),
        rules=[],
        memory=SimpleNamespace(commands={}),
        commands={},
    )


def _ready_agent_env() -> MagicMock:
    env = MagicMock()
    env.is_ready.return_value = True
    env.status.return_value = {
        "status": "ready",
        "compatibility_status": "current",
        "compatibility_reason": "Managed agent environment matches the current CLI compatibility stamp.",
        "repair_action": "none",
        "repair_command": None,
        "repair_reason": "Managed agent runtime is current.",
    }
    env.inject_into_sys_path.return_value = None
    return env


@pytest.mark.asyncio
async def test_run_agent_adds_mcp_tools_when_enabled() -> None:
    with tempfile.TemporaryDirectory() as td:
        mcp_servers = [
            MCPServerConfig(
                name="local-mcp",
                command="python",
                args=[],
                env={},
                tools=[MCPToolConfig(name="query_db", parameters={"type": "object"})],
            )
        ]
        mock_client = MagicMock()
        build_agent_tools_kwargs = {}

        def fake_build_agent_tools(**kwargs):
            build_agent_tools_kwargs.update(kwargs)
            return [SimpleNamespace(name="query_db")]

        with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
            with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                with patch("beep.agent.loop.AgentEnvironmentManager", return_value=_ready_agent_env()):
                    with patch(
                        "beep.agent.loop.build_agent_tools",
                        side_effect=fake_build_agent_tools,
                    ):
                        with patch(
                            "beep.agent.loop.run_graph",
                            new=AsyncMock(
                                return_value={
                                    "steps_executed": 1,
                                    "tool_calls_executed": 0,
                                    "run_reason": "completed",
                                    "final_message": "done",
                                }
                            ),
                        ) as run_graph_mock:
                            await run_agent(
                                mock_client,
                                "test goal",
                                mcp_enabled=True,
                                mcp_servers=mcp_servers,
                            )
                            tools_arg = run_graph_mock.await_args.kwargs["tools"]
                            assert build_agent_tools_kwargs["mcp_enabled"] is True
                            assert build_agent_tools_kwargs["mcp_servers"] == mcp_servers
                            assert "query_db" in {tool.name for tool in tools_arg}


@pytest.mark.asyncio
async def test_run_agent_sets_default_coding_metadata() -> None:
    with tempfile.TemporaryDirectory() as td:
        mock_client = MagicMock()
        with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
            with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                with patch("beep.agent.loop.AgentEnvironmentManager", return_value=_ready_agent_env()):
                    with patch(
                        "beep.agent.loop.run_graph",
                        new=AsyncMock(
                            return_value={
                                "steps_executed": 1,
                                "tool_calls_executed": 0,
                                "run_reason": "completed",
                                "final_message": "done",
                            }
                        ),
                    ) as run_graph_mock:
                        await run_agent(mock_client, "goal")
                        build_backend_kwargs = run_graph_mock.await_args.kwargs
                        build_backend = build_backend_kwargs["backend"]
                        assert build_backend is not None


@pytest.mark.asyncio
async def test_run_agent_read_only_sandbox_filters_mutating_tools() -> None:
    with tempfile.TemporaryDirectory() as td:
        mock_client = MagicMock()
        with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
            with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                with patch("beep.agent.loop.AgentEnvironmentManager", return_value=_ready_agent_env()):
                    with patch(
                        "beep.agent.loop.run_graph",
                        new=AsyncMock(
                            return_value={
                                "steps_executed": 1,
                                "tool_calls_executed": 0,
                                "run_reason": "completed",
                                "final_message": "done",
                            }
                        ),
                    ) as run_graph_mock:
                        await run_agent(
                            mock_client,
                            "test goal",
                            sandbox_mode=SandboxMode.READ_ONLY,
                        )
                        tools_arg = run_graph_mock.await_args.kwargs["tools"]
                        names = {tool.name for tool in tools_arg}
                        assert "file_write" not in names
                        assert "file_edit" not in names
                        assert "shell" not in names
                        assert run_graph_mock.await_args.kwargs["sandbox_mode"] == SandboxMode.READ_ONLY


@pytest.mark.asyncio
async def test_run_agent_merges_partial_coding_metadata() -> None:
    with tempfile.TemporaryDirectory() as td:
        mock_client = MagicMock()
        with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
            with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                with patch("beep.agent.loop.AgentEnvironmentManager", return_value=_ready_agent_env()):
                    with patch("beep.agent.loop.build_agent_backend") as build_backend:
                        with patch(
                            "beep.agent.loop.run_graph",
                            new=AsyncMock(
                                return_value={
                                    "steps_executed": 1,
                                    "tool_calls_executed": 0,
                                    "run_reason": "completed",
                                    "final_message": "done",
                                }
                            ),
                        ):
                            await run_agent(
                                mock_client,
                                "goal",
                                coding_assistant={"project_id": 123},
                            )
                            _, kwargs = build_backend.call_args
                            assert kwargs["coding_assistant"]["project_id"] == 123
                            assert kwargs["coding_assistant"]["workspace_root"] == str(Path(td))
                            assert kwargs["coding_assistant"]["interaction_mode"] == "agent"


@pytest.mark.asyncio
async def test_run_agent_passes_workspace_system_prompt() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    with (
        patch("beep.agent.loop.AgentEnvironmentManager", return_value=env),
        patch("beep.agent.loop.find_workspace_root", return_value=Path.cwd()),
        patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()),
        patch("beep.agent.loop.build_agent_backend", return_value=backend),
        patch("beep.agent.loop.build_workspace_system_prompt", return_value="workspace sys"),
        patch(
            "beep.agent.loop.run_graph",
            new=AsyncMock(
                return_value={
                    "steps_executed": 1,
                    "tool_calls_executed": 0,
                    "run_reason": "completed",
                    "final_message": "done",
                }
            ),
        ) as run_graph_mock,
    ):
        await run_agent(MagicMock(), "inspect")
        assert run_graph_mock.await_args.kwargs["system_prompt"] == "workspace sys"
        backend.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_agent_applies_bundle_manifest_provider_options_and_tool_policy() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    build_agent_tools_kwargs: dict[str, object] = {}
    bundle_manifest = PortableAgentBundleManifest.from_dict(
        {
            "agent_id": "portable-agent",
            "name": "Portable Agent",
            "system_prompt": "bundle sys",
            "model": {
                "provider_key": "openrouter",
                "model_id": "anthropic/claude-sonnet-4",
                "provider_options": {"reasoning": {"effort": "high"}},
            },
            "tool_policy": {
                "allowed_categories": ["workspace"],
                "blocked_tools": ["search"],
                "allow_mcp_tools": False,
                "allow_builtin_tools": False,
            },
        }
    )

    def fake_build_agent_tools(**kwargs):
        build_agent_tools_kwargs.update(kwargs)
        return [SimpleNamespace(name="plugin_tool", category="workspace")]

    with (
        patch("beep.agent.loop.AgentEnvironmentManager", return_value=env),
        patch("beep.agent.loop.find_workspace_root", return_value=Path.cwd()),
        patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()),
        patch("beep.agent.loop.build_agent_backend", return_value=backend),
        patch("beep.agent.loop.build_agent_tools", side_effect=fake_build_agent_tools),
        patch("beep.agent.loop.build_workspace_system_prompt", return_value="workspace sys"),
        patch(
            "beep.agent.loop.run_graph",
            new=AsyncMock(
                return_value={
                    "steps_executed": 1,
                    "tool_calls_executed": 0,
                    "run_reason": "completed",
                    "final_message": "done",
                }
            ),
        ) as run_graph_mock,
    ):
        await run_agent(MagicMock(), "inspect", bundle_manifest=bundle_manifest, mcp_enabled=True)

    assert build_agent_tools_kwargs["allow_builtin_tools"] is False
    assert build_agent_tools_kwargs["blocked_tools"] == ["search"]
    assert build_agent_tools_kwargs["categories"] == ["workspace"]
    assert build_agent_tools_kwargs["mcp_enabled"] is False
    assert run_graph_mock.await_args.kwargs["system_prompt"] == "bundle sys\n\nworkspace sys"
    assert run_graph_mock.await_args.kwargs["provider_options"] == {"reasoning": {"effort": "high"}}
    backend.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_agent_requires_ready_managed_environment() -> None:
    env = MagicMock()
    env.is_ready.return_value = False
    env.status.return_value = {
        "status": "not_created",
        "compatibility_status": "not_created",
        "compatibility_reason": "Managed agent environment has not been created yet.",
        "repair_action": "setup",
        "repair_command": "beep agent setup",
        "repair_reason": "Managed agent environment does not exist yet.",
    }
    env.inject_into_sys_path.return_value = None
    with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
        with pytest.raises(RuntimeError, match="beep agent setup"):
            await run_agent(MagicMock(), "inspect")


@pytest.mark.asyncio
async def test_run_agent_rejects_stale_managed_environment() -> None:
    env = MagicMock()
    env.status.return_value = {
        "status": "ready",
        "compatibility_status": "stale",
        "compatibility_reason": "Compatibility stamp mismatch: cli_version='0.0.0' expected '0.1.0'",
        "repair_action": "setup",
        "repair_command": "beep agent setup",
        "repair_reason": "Managed runtime compatibility drift detected; refresh the managed runtime.",
    }
    env.inject_into_sys_path.return_value = None
    with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
        with pytest.raises(RuntimeError, match="beep agent setup"):
            await run_agent(MagicMock(), "inspect")
    env.inject_into_sys_path.assert_not_called()


@pytest.mark.asyncio
async def test_run_agent_rejects_metadata_incompatible_runtime_with_reinstall_guidance() -> None:
    env = MagicMock()
    env.status.return_value = {
        "status": "ready",
        "compatibility_status": "stale",
        "compatibility_reason": "Compatibility stamp mismatch: metadata_version=0 expected 1",
        "repair_action": "reinstall",
        "repair_command": "beep agent reinstall runtime",
        "repair_reason": "Managed runtime compatibility metadata changed; rebuild the managed runtime from scratch.",
    }
    env.inject_into_sys_path.return_value = None
    with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
        with pytest.raises(RuntimeError, match="beep agent reinstall runtime"):
            await run_agent(MagicMock(), "inspect")
    env.inject_into_sys_path.assert_not_called()


@pytest.mark.asyncio
async def test_run_agent_builds_openai_compatible_backend_from_config() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                    with patch("beep.agent.loop.build_agent_backend", return_value=backend) as build_backend:
                        with patch(
                            "beep.agent.loop.run_graph",
                            new=AsyncMock(
                                return_value={
                                    "steps_executed": 1,
                                    "tool_calls_executed": 0,
                                    "run_reason": "completed",
                                    "final_message": "done",
                                }
                            ),
                        ) as run_graph_mock:
                            config = BeepConfig(
                                agent_backend="openai-compatible",
                                agent_base_url="http://provider.test",
                                agent_api_key="provider-token",
                                agent_model="model-x",
                            )
                            await run_agent(None, "goal", config=config)
                            build_backend.assert_called_once()
                            assert build_backend.call_args.args[0] == config
                            assert run_graph_mock.await_args.kwargs["backend"] == backend
                            backend.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_resume_agent_delegates_to_resume_graph() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                    with patch("beep.agent.loop.build_agent_backend", return_value=backend):
                        with patch(
                            "beep.agent.loop.resume_graph",
                            new=AsyncMock(
                                return_value={
                                    "steps_executed": 2,
                                    "tool_calls_executed": 1,
                                    "run_reason": "completed",
                                    "final_message": "done",
                                }
                            ),
                        ) as resume_graph_mock:
                            result = await resume_agent(MagicMock(), "thread-123")
                            assert result.reason == "completed"
                            assert resume_graph_mock.await_args.kwargs["session_id"] == "thread-123"
                            assert resume_graph_mock.await_args.kwargs["backend"] == backend
                            backend.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_agent_closes_backend_when_graph_fails() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                    with patch("beep.agent.loop.build_agent_backend", return_value=backend):
                        with patch(
                            "beep.agent.loop.run_graph",
                            new=AsyncMock(side_effect=RuntimeError("graph failed")),
                        ):
                            with pytest.raises(RuntimeError, match="graph failed"):
                                await run_agent(None, "goal")
                            backend.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_agent_passes_workspace_plugin_runtime_to_tool_factory() -> None:
    env = _ready_agent_env()
    runtime = _runtime()
    backend = MagicMock()
    backend.close = AsyncMock()
    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=runtime):
                    with patch("beep.agent.loop.build_agent_backend", return_value=backend):
                        with patch("beep.agent.loop.build_agent_tools", return_value=[] ) as build_tools:
                            with patch(
                                "beep.agent.loop.run_graph",
                                new=AsyncMock(
                                    return_value={
                                        "steps_executed": 1,
                                        "tool_calls_executed": 0,
                                        "run_reason": "completed",
                                        "final_message": "done",
                                    }
                                ),
                            ):
                                await run_agent(None, "goal")
                                assert build_tools.call_args.kwargs["plugin_runtime"] is runtime.plugin_runtime


@pytest.mark.asyncio
async def test_run_agent_rejects_backend_without_tool_calling_capability() -> None:
    env = _ready_agent_env()
    provider_descriptor = ProviderDescriptor(
        key="no-tools",
        display_name="No Tools Provider",
        capabilities=ProviderCapabilities(
            chat_completion=CapabilityFlag(True, "Chat completions exist."),
            tool_calling=CapabilityFlag(False, "This provider cannot execute tool calls."),
            streaming=CapabilityFlag(False, "Streaming unavailable."),
            structured_output=CapabilityFlag(False, "Structured output unavailable."),
            vision=CapabilityFlag(False, "Vision unavailable."),
            embeddings=CapabilityFlag(False, "Embeddings unavailable."),
            local_model_runtime=CapabilityFlag(False, "No local runtime."),
        ),
    )
    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                    with patch(
                        "beep.agent.loop.build_provider_descriptor",
                        return_value=provider_descriptor,
                    ):
                        with pytest.raises(RuntimeError, match="tool-calling support"):
                            await run_agent(MagicMock(), "goal")


@pytest.mark.asyncio
async def test_run_agent_uses_runtime_plugin_provider() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    provider_descriptor = ProviderDescriptor(
        key="custom-provider",
        display_name="Custom Provider",
        capabilities=ProviderCapabilities(
            chat_completion=CapabilityFlag(True, "Chat completions exist."),
            tool_calling=CapabilityFlag(True, "This provider supports tool calls."),
            streaming=CapabilityFlag(False, "Streaming unavailable."),
            structured_output=CapabilityFlag(False, "Structured output unavailable."),
            vision=CapabilityFlag(False, "Vision unavailable."),
            embeddings=CapabilityFlag(False, "Embeddings unavailable."),
            local_model_runtime=CapabilityFlag(False, "No local runtime."),
        ),
    )

    class _CustomProvider:
        def is_configured(self, config: object) -> bool:
            return True

        def describe(self, config: object) -> ProviderDescriptor:
            return provider_descriptor

        def build_backend(self, config: object, *, client: object = None, coding_assistant: dict[str, object] | None = None) -> object:
            return backend

    registry = SimpleNamespace(
        get_tools=lambda workspace_root=None: [],
        get_backend_provider=lambda key: _CustomProvider() if key == "custom-provider" else None,
    )
    runtime = _runtime()
    runtime.plugin_runtime = SimpleNamespace(registry=registry)

    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=runtime):
                    with patch(
                        "beep.agent.loop.run_graph",
                        new=AsyncMock(
                            return_value={
                                "steps_executed": 1,
                                "tool_calls_executed": 0,
                                "run_reason": "completed",
                                "final_message": "done",
                            }
                        ),
                    ) as run_graph_mock:
                        config = BeepConfig(agent_backend="custom-provider")
                        await run_agent(None, "goal", config=config)
                        assert run_graph_mock.await_args.kwargs["backend"] is backend
                        backend.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_agent_forwards_selected_provider_options() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                    with patch("beep.agent.loop.build_agent_backend", return_value=backend):
                        with patch(
                            "beep.agent.loop.run_graph",
                            new=AsyncMock(
                                return_value={
                                    "steps_executed": 1,
                                    "tool_calls_executed": 0,
                                    "run_reason": "completed",
                                    "final_message": "done",
                                }
                            ),
                        ) as run_graph_mock:
                            config = BeepConfig(
                                agent_backend="openai-compatible",
                                agent_base_url="http://provider.test",
                                agent_api_key="provider-token",
                                agent_model="model-x",
                                agent_reasoning_effort="high",
                                agent_parallel_tool_calls=False,
                            )
                            await run_agent(None, "goal", config=config)

    assert run_graph_mock.await_args.kwargs["provider_options"] == {
        "reasoning": {"effort": "high"},
        "parallel_tool_calls": False,
    }


@pytest.mark.asyncio
async def test_run_agent_forwards_response_format_and_initial_user_content() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    initial_user_content = [
        {"type": "text", "text": "Focus on the failing assertions only."},
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,AAAA"},
        },
    ]
    response_format = {"type": "json_object"}

    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                    with patch("beep.agent.loop.build_agent_backend", return_value=backend):
                        with patch(
                            "beep.agent.loop.run_graph",
                            new=AsyncMock(
                                return_value={
                                    "steps_executed": 1,
                                    "tool_calls_executed": 0,
                                    "run_reason": "completed",
                                    "final_message": "done",
                                }
                            ),
                        ) as run_graph_mock:
                            await run_agent(
                                None,
                                "inspect this screenshot",
                                response_format=response_format,
                                initial_user_content=initial_user_content,
                            )

    assert run_graph_mock.await_args.kwargs["response_format"] == response_format
    assert run_graph_mock.await_args.kwargs["initial_user_content"] == initial_user_content


@pytest.mark.asyncio
async def test_resume_agent_forwards_response_format() -> None:
    env = _ready_agent_env()
    backend = MagicMock()
    backend.close = AsyncMock()
    response_format = {"type": "json_object"}

    with tempfile.TemporaryDirectory() as td:
        with patch("beep.agent.loop.AgentEnvironmentManager", return_value=env):
            with patch("beep.agent.loop.find_workspace_root", return_value=Path(td)):
                with patch("beep.agent.loop.get_workspace_runtime", return_value=_runtime()):
                    with patch("beep.agent.loop.build_agent_backend", return_value=backend):
                        with patch(
                            "beep.agent.loop.resume_graph",
                            new=AsyncMock(
                                return_value={
                                    "steps_executed": 2,
                                    "tool_calls_executed": 1,
                                    "run_reason": "completed",
                                    "final_message": "done",
                                }
                            ),
                        ) as resume_graph_mock:
                            await resume_agent(
                                None,
                                "thread-structured",
                                response_format=response_format,
                            )

    assert resume_graph_mock.await_args.kwargs["response_format"] == response_format
