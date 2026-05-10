"""Agent tool construction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from beep.agent.planning import TodoList
from beep.agent.subagents.dispatcher import SubAgentDispatcher
from beep.agent.tools.base import BaseTool
from beep.agent.tools.code_snippets import build_snippet_tools
from beep.agent.tools.context_tool import ContextTool
from beep.agent.tools.dispatch_agent import DispatchAgentTool
from beep.agent.tools.file_edit import FileEditTool, SingleEditTool
from beep.agent.tools.file_read import FileReadTool
from beep.agent.tools.file_write import FileWriteTool
from beep.agent.tools.git_tool import GitTool
from beep.agent.tools.glob_files import GlobFilesTool
from beep.agent.tools.list_directory import ListDirectoryTool
from beep.agent.tools.project_templates import build_template_tools
from beep.agent.tools.search import SearchTool
from beep.agent.tools.shell import ShellTool
from beep.agent.tools.todo_tool import TodoWriteTool
from beep.plugins.runtime import PluginRuntime

logger = logging.getLogger(__name__)


def _get_template_registry() -> ProjectTemplateRegistry:
    from beep.app_service import get_app_service

    return get_app_service().template_registry


def _declares_read_only_safety(tool: object) -> bool:
    return "read_only_safe" in getattr(tool, "__dict__", {}) or "read_only_safe" in vars(type(tool))


def _is_read_only_safe_tool(tool: BaseTool) -> bool:
    module_name = type(tool).__module__
    if module_name.startswith("beep.agent.tools."):
        return bool(getattr(tool, "read_only_safe", True))
    if not _declares_read_only_safety(tool):
        logger.debug(
            "Skipping tool '%s' in read-only mode because it does not declare read_only_safe.",
            getattr(tool, "name", type(tool).__name__),
        )
        return False
    return bool(getattr(tool, "read_only_safe", False))


def get_default_tools(
    workspace_root: Path,
    *,
    read_only: bool = False,
    todo_list: TodoList | None = None,
    subagent_dispatcher: SubAgentDispatcher | None = None,
    backend: Any | None = None,
    system_prompt: str = "",
    session_id: str = "",
) -> list[BaseTool]:
    """Get the default set of agent tools.

    Parameters
    ----------
    workspace_root:
        Absolute path that the tools treat as the sandboxed workspace.
    read_only:
        When True, omit write-capable tools (file_write, file_edit,
        single_edit, shell, and git write operations).  Use for review-only
        or analysis agents that must never mutate files.
    todo_list:
        Shared TodoList instance injected into TodoWriteTool.
    subagent_dispatcher:
        Shared SubAgentDispatcher instance injected into DispatchAgentTool.
    backend:
        Agent backend for sub-agent dispatch.
    system_prompt:
        System prompt to propagate to dispatched sub-agents.
    session_id:
        Session ID for sub-agent checkpointing.
    """
    tools: list[BaseTool] = [
        FileReadTool(workspace_root=workspace_root),
        ContextTool(workspace_root=workspace_root),
        SearchTool(workspace_root=workspace_root),
        ListDirectoryTool(workspace_root=workspace_root),
        GlobFilesTool(workspace_root=workspace_root),
        GitTool(workspace_root=workspace_root),
        TodoWriteTool(todo_list=todo_list if todo_list is not None else TodoList()),
        DispatchAgentTool(
            dispatcher=subagent_dispatcher
            or SubAgentDispatcher(
                workspace_root=workspace_root,
                all_tools=[],
            ),
            backend=backend,
            system_prompt=system_prompt,
            session_id=session_id,
        ),
    ]
    if not read_only:
        tools += [
            FileWriteTool(workspace_root=workspace_root),
            FileEditTool(workspace_root=workspace_root),
            SingleEditTool(workspace_root=workspace_root),
            ShellTool(workspace_root=workspace_root),
        ]
    return tools


def build_agent_tools(
    *,
    workspace_root: Path,
    plugin_runtime: PluginRuntime,
    mcp_enabled: bool = False,
    mcp_servers: list[Any] | None = None,
    read_only: bool = False,
    categories: list[str] | None = None,
    allow_builtin_tools: bool = True,
    blocked_tools: list[str] | None = None,
    todo_list: TodoList | None = None,
    subagent_dispatcher: SubAgentDispatcher | None = None,
    backend: Any | None = None,
    system_prompt: str = "",
    session_id: str = "",
) -> list[BaseTool]:
    """Compose local, plugin, and optional MCP tools for an agent run.

    Parameters
    ----------
    categories:
        When provided, only tools whose ``category`` property is in this list
        are returned.  ``None`` means no filtering (all tools included).
    """
    tools: list[BaseTool] = []
    if allow_builtin_tools:
        tools.extend(
            get_default_tools(
                workspace_root,
                read_only=read_only,
                todo_list=todo_list,
                subagent_dispatcher=subagent_dispatcher,
                backend=backend,
                system_prompt=system_prompt,
                session_id=session_id,
            )
        )
        tools.extend(build_snippet_tools())
        tools.extend(build_template_tools(registry=_get_template_registry()))
    get_workspace_intelligence_tools = getattr(
        plugin_runtime.registry,
        "get_workspace_intelligence_tools",
        None,
    )
    if callable(get_workspace_intelligence_tools):
        tools.extend(get_workspace_intelligence_tools(workspace_root))
    tools.extend(plugin_runtime.registry.get_tools(workspace_root=workspace_root))
    if mcp_enabled and mcp_servers:
        try:
            from beep.app_service import get_app_service
        except ImportError:
            logger.debug("MCP package not installed; skipping MCP tools.")
        else:
            mcp_client = get_app_service().mcp_client(mcp_servers)
            tools.extend(mcp_client.to_agent_tools())
    if read_only:
        tools = [tool for tool in tools if _is_read_only_safe_tool(tool)]
    if categories is not None:
        tools = [t for t in tools if t.category in categories]
    if blocked_tools:
        blocked = {name.strip() for name in blocked_tools if name.strip()}
        tools = [tool for tool in tools if tool.name not in blocked]
    return tools
