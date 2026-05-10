"""Dependency bundle for patchable LangGraph runner behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from beep.agent.tools.base import ToolResult
from beep.permissions.manager import PermissionDecision


@dataclass(frozen=True)
class GraphRuntimeDependencies:
    adapt_tools: Callable[..., list[Any]]
    evaluate_permission: Callable[[str, dict[str, Any]], PermissionDecision]
    requires_approval: Callable[[str, dict[str, Any]], bool]
    request_approval: Callable[[str, dict[str, Any]], bool]
    agent_messages_to_langchain_messages: Callable[[list[dict[str, Any]]], list[Any]]
    agent_dict_to_langchain_message: Callable[[dict[str, Any]], Any]
    langchain_messages_to_agent_dicts: Callable[[list[Any]], list[dict[str, Any]]]
    langchain_message_to_agent_dict: Callable[[Any], dict[str, Any]]
    tool_result_to_langchain_message: Callable[..., Any]
    render_response: Callable[..., None]
    append_message: Callable[[str, dict[str, Any]], Any]
    log_event: Callable[..., None]
    format_tool_result: Callable[[str, ToolResult, int], None]
    file_touch_tools: frozenset[str]
    console: Any