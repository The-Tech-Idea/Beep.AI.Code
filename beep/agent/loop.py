"""Managed entrypoints for the LangGraph-backed autonomous agent runtime."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from beep.agent.backends import build_agent_backend
from beep.agent.bundle_contract import PortableAgentBundleManifest
from beep.agent.environment import AgentEnvironmentManager
from beep.agent.graph_runner import InitialUserContent
from beep.agent.planning import TodoList
from beep.agent.provider_options import build_agent_provider_options
from beep.agent.provider_capabilities import build_provider_descriptor
from beep.agent.graph import resume_graph, run_graph
from beep.agent.tools.base import BaseTool
from beep.agent.tools.factory import build_agent_tools
from beep.api.client import BeepAPIClient
from beep.coding.prompt_context import build_workspace_system_prompt
from beep.config import BeepConfig
from beep.permissions.manager import SandboxMode, coerce_sandbox_mode
from beep.runtime.workspace import get_workspace_runtime
from beep.sessions.history import create_session_id
from beep.workspace.detector import find_workspace_root

DEFAULT_MAX_STEPS = 20
DEFAULT_MAX_TOOL_CALLS_PER_STEP = 20
DEFAULT_MAX_TOOL_CALLS_TOTAL = 200

# Anti-loop / anti-hang defaults
DEFAULT_STEP_TIMEOUT = 120  # seconds to wait for a single API call
DEFAULT_MAX_REPEATED_CALLS = 3  # abort when same (tool, args) seen this many times
DEFAULT_MAX_CONSECUTIVE_FAILURES = 5  # abort when this many steps in a row all fail
DEFAULT_MAX_TOOL_OUTPUT_CHARS = 8_000  # cap per-tool message content to avoid context blowup


@dataclass
class AgentRunResult:
    """Summary of a completed agent run."""

    steps_executed: int
    tool_calls_executed: int
    reason: str
    final_message: str | None = None


async def _close_backend(backend: Any) -> None:
    close = getattr(backend, "close", None)
    if not callable(close):
        return
    result = close()
    if inspect.isawaitable(result):
        await result


async def run_agent(
    client: BeepAPIClient | None,
    goal: str,
    *,
    config: BeepConfig | None = None,
    workspace_root: Path | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    step_timeout: float = DEFAULT_STEP_TIMEOUT,
    max_repeated_calls: int = DEFAULT_MAX_REPEATED_CALLS,
    max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    max_tool_output_chars: int = DEFAULT_MAX_TOOL_OUTPUT_CHARS,
    auto_approve: bool = False,
    sandbox_mode: SandboxMode | str | bool | None = SandboxMode.WORKSPACE_WRITE,
    plugins_enabled: bool = True,
    coding_assistant: dict[str, Any] | None = None,
    mcp_enabled: bool = False,
    mcp_servers: list[Any] | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
    initial_user_content: InitialUserContent | None = None,
    bundle_manifest: PortableAgentBundleManifest | None = None,
) -> AgentRunResult:
    """Run an agent session.

    `response_format` forwards structured-output hints to compatible providers.
    `initial_user_content` lets callers attach richer multimodal content to the
    first user turn while keeping the goal-oriented agent instructions intact.
    """
    effective_sandbox_mode = coerce_sandbox_mode(sandbox_mode)
    workspace_root, runtime, backend, tools, system_prompt, todo_list, effective_config = _prepare_agent_runtime(
        client,
        config=config,
        workspace_root=workspace_root,
        sandbox_mode=effective_sandbox_mode,
        plugins_enabled=plugins_enabled,
        coding_assistant=coding_assistant,
        mcp_enabled=mcp_enabled,
        mcp_servers=mcp_servers,
        skill_query=goal,
        bundle_manifest=bundle_manifest,
    )
    session_id = create_session_id()
    provider_options = (
        dict(bundle_manifest.model.provider_options)
        if bundle_manifest is not None and bundle_manifest.model.provider_options
        else build_agent_provider_options(effective_config)
    )
    try:
        final_state = await run_graph(
            goal=goal,
            initial_user_content=initial_user_content,
            backend=backend,
            tools=tools,
            workspace_root=workspace_root,
            system_prompt=system_prompt,
            workspace_rules=runtime.rules,
            session_id=session_id,
            max_steps=max_steps,
            max_tool_calls_per_step=DEFAULT_MAX_TOOL_CALLS_PER_STEP,
            max_tool_calls_total=DEFAULT_MAX_TOOL_CALLS_TOTAL,
            step_timeout=step_timeout,
            max_repeated_calls=max_repeated_calls,
            max_consecutive_failures=max_consecutive_failures,
            max_tool_output_chars=max_tool_output_chars,
            auto_approve=auto_approve,
            sandbox_mode=effective_sandbox_mode,
            todo_list=todo_list,
            auto_verify=auto_verify,
            response_format=response_format,
            provider_options=provider_options,
        )
    finally:
        await _close_backend(backend)
    return AgentRunResult(
        steps_executed=final_state["steps_executed"],
        tool_calls_executed=final_state["tool_calls_executed"],
        reason=final_state["run_reason"] or "completed",
        final_message=final_state["final_message"],
    )


async def resume_agent(
    client: BeepAPIClient | None,
    session_id: str,
    *,
    config: BeepConfig | None = None,
    workspace_root: Path | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    step_timeout: float = DEFAULT_STEP_TIMEOUT,
    max_repeated_calls: int = DEFAULT_MAX_REPEATED_CALLS,
    max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    max_tool_output_chars: int = DEFAULT_MAX_TOOL_OUTPUT_CHARS,
    auto_approve: bool = False,
    sandbox_mode: SandboxMode | str | bool | None = SandboxMode.WORKSPACE_WRITE,
    plugins_enabled: bool = True,
    coding_assistant: dict[str, Any] | None = None,
    mcp_enabled: bool = False,
    mcp_servers: list[Any] | None = None,
    auto_verify: bool = False,
    response_format: dict[str, Any] | None = None,
) -> AgentRunResult:
    """Resume an existing checkpointed agent thread."""
    effective_sandbox_mode = coerce_sandbox_mode(sandbox_mode)
    workspace_root, runtime, backend, tools, system_prompt, todo_list, effective_config = _prepare_agent_runtime(
        client,
        config=config,
        workspace_root=workspace_root,
        sandbox_mode=effective_sandbox_mode,
        plugins_enabled=plugins_enabled,
        coding_assistant=coding_assistant,
        mcp_enabled=mcp_enabled,
        mcp_servers=mcp_servers,
        skill_query=None,
    )
    provider_options = build_agent_provider_options(effective_config)
    try:
        final_state = await resume_graph(
            backend=backend,
            tools=tools,
            workspace_root=workspace_root,
            system_prompt=system_prompt,
            workspace_rules=runtime.rules,
            session_id=session_id,
            max_steps=max_steps,
            max_tool_calls_per_step=DEFAULT_MAX_TOOL_CALLS_PER_STEP,
            max_tool_calls_total=DEFAULT_MAX_TOOL_CALLS_TOTAL,
            step_timeout=step_timeout,
            max_repeated_calls=max_repeated_calls,
            max_consecutive_failures=max_consecutive_failures,
            max_tool_output_chars=max_tool_output_chars,
            auto_approve=auto_approve,
            sandbox_mode=effective_sandbox_mode,
            todo_list=todo_list,
            auto_verify=auto_verify,
            response_format=response_format,
            provider_options=provider_options,
        )
    finally:
        await _close_backend(backend)
    return AgentRunResult(
        steps_executed=final_state["steps_executed"],
        tool_calls_executed=final_state["tool_calls_executed"],
        reason=final_state["run_reason"] or "completed",
        final_message=final_state["final_message"],
    )


def _prepare_agent_runtime(
    client: BeepAPIClient | None,
    *,
    config: BeepConfig | None,
    workspace_root: Path | None,
    sandbox_mode: SandboxMode,
    plugins_enabled: bool,
    coding_assistant: dict[str, Any] | None,
    mcp_enabled: bool,
    mcp_servers: list[Any] | None,
    skill_query: str | None,
    bundle_manifest: PortableAgentBundleManifest | None = None,
) -> tuple[Path, Any, Any, list[BaseTool], str, TodoList, BeepConfig]:
    agent_environment = AgentEnvironmentManager()
    environment_status = agent_environment.status()
    if environment_status.get("status") != "ready":
        repair_reason = str(
            environment_status.get("repair_reason")
            or environment_status.get("compatibility_reason")
            or "Managed agent environment not ready."
        )
        repair_command = str(environment_status.get("repair_command") or "beep agent setup")
        raise RuntimeError(
            f'{repair_reason} Run "{repair_command}" before using the autonomous agent.'
        )
    if environment_status.get("compatibility_status") != "current":
        reason = str(
            environment_status.get("repair_reason")
            or environment_status.get("compatibility_reason")
            or "Managed agent environment is stale."
        )
        repair_command = str(environment_status.get("repair_command") or "beep agent setup")
        raise RuntimeError(f'{reason} Run "{repair_command}" before using the autonomous agent.')
    agent_environment.inject_into_sys_path()

    effective_workspace_root = workspace_root or find_workspace_root()
    runtime = get_workspace_runtime(effective_workspace_root, plugins_enabled=plugins_enabled)
    candidate_config = config if isinstance(config, BeepConfig) else None
    if candidate_config is None:
        client_config = getattr(client, "_config", None)
        if isinstance(client_config, BeepConfig):
            candidate_config = client_config
    effective_config = candidate_config or BeepConfig()
    provider_descriptor = build_provider_descriptor(
        effective_config,
        plugin_registry=runtime.plugin_runtime.registry,
    )
    if not provider_descriptor.capabilities.tool_calling.exists:
        raise RuntimeError(
            f'Configured agent backend "{provider_descriptor.display_name}" does not support tool calling; '
            "the autonomous agent requires tool-calling support."
        )
    default_coding_assistant = {
        "workspace_root": str(effective_workspace_root),
        "interaction_mode": "agent",
    }
    effective_coding_assistant = dict(default_coding_assistant)
    if coding_assistant:
        effective_coding_assistant.update(coding_assistant)
    backend = build_agent_backend(
        effective_config,
        client=client,
        coding_assistant=effective_coding_assistant,
        plugin_registry=runtime.plugin_runtime.registry,
    )
    todo_list = TodoList()
    allowed_categories = None
    blocked_tools = None
    allow_builtin_tools = True
    allow_mcp_tools = mcp_enabled
    bundle_prompt = ""
    if bundle_manifest is not None:
        allowed_categories = bundle_manifest.tool_policy.allowed_categories or None
        blocked_tools = bundle_manifest.tool_policy.blocked_tools or None
        allow_builtin_tools = bundle_manifest.tool_policy.allow_builtin_tools
        allow_mcp_tools = mcp_enabled and bundle_manifest.tool_policy.allow_mcp_tools
        bundle_prompt = bundle_manifest.system_prompt.strip()
    tools = build_agent_tools(
        workspace_root=effective_workspace_root,
        plugin_runtime=runtime.plugin_runtime,
        mcp_enabled=allow_mcp_tools,
        mcp_servers=mcp_servers,
        read_only=sandbox_mode == SandboxMode.READ_ONLY,
        categories=allowed_categories,
        allow_builtin_tools=allow_builtin_tools,
        blocked_tools=blocked_tools,
        todo_list=todo_list,
    )
    workspace_system_prompt = build_workspace_system_prompt(
        "agent",
        effective_workspace_root,
        tools=tools,
        skill_query=skill_query,
    )
    system_prompt = (
        f"{bundle_prompt}\n\n{workspace_system_prompt}"
        if bundle_prompt
        else workspace_system_prompt
    )
    return effective_workspace_root, runtime, backend, tools, system_prompt, todo_list, effective_config
