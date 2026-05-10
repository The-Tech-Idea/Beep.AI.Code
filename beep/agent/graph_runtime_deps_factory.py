"""Shared factory for GraphRuntimeDependencies — single source of truth."""

from __future__ import annotations

from typing import Any

from beep.agent.graph_runtime_dependencies import GraphRuntimeDependencies
from beep.agent.graph_support import _FILE_TOUCH_TOOLS, _format_tool_result
from beep.agent.message_adapter import (
    agent_dict_to_langchain_message,
    agent_messages_to_langchain_messages,
    langchain_message_to_agent_dict,
    langchain_messages_to_agent_dicts,
    tool_result_to_langchain_message,
)
from beep.agent.tool_adapter import adapt_tools
from beep.chat.stream_renderer import render_response
from beep.permissions.manager import PermissionDecision
from beep.sessions.history import append_message
from beep.utils.console import get_console
from beep.utils.json_logging import log_event


def make_graph_runtime_dependencies() -> GraphRuntimeDependencies:
    from beep.agent.approval import request_approval, requires_approval

    def _evaluate_permission(tool_name: str, arguments: dict[str, Any]) -> PermissionDecision:
        if requires_approval(tool_name, arguments):
            return PermissionDecision(True, True, "Requires approval")
        return PermissionDecision(True, False, "Auto-approved")

    return GraphRuntimeDependencies(
        adapt_tools=adapt_tools,
        evaluate_permission=_evaluate_permission,
        requires_approval=requires_approval,
        request_approval=request_approval,
        agent_messages_to_langchain_messages=agent_messages_to_langchain_messages,
        agent_dict_to_langchain_message=agent_dict_to_langchain_message,
        langchain_messages_to_agent_dicts=langchain_messages_to_agent_dicts,
        langchain_message_to_agent_dict=langchain_message_to_agent_dict,
        tool_result_to_langchain_message=tool_result_to_langchain_message,
        render_response=render_response,
        append_message=append_message,
        log_event=log_event,
        format_tool_result=_format_tool_result,
        file_touch_tools=_FILE_TOUCH_TOOLS,
        console=get_console(),
    )
