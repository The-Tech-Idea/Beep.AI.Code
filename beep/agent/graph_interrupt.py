"""Human-in-the-loop interrupt support for the LangGraph agent runtime.

Provides the interrupt-based approval pattern (LangGraph 0.4+ recommended)
as an alternative to the node-based approval flow. Enables async approval
flows (TUI, web UI) instead of blocking CLI prompts.
"""

from __future__ import annotations

import json
from typing import Any

from beep.agent.graph_support import AgentGraphState


def interrupt_approval_node(runner: Any, state: AgentGraphState) -> dict[str, Any]:
    """Node that uses LangGraph interrupt() for human approval.

    This replaces the synchronous approval_node with the modern
    interrupt() pattern. When called, graph execution pauses, state
    is saved, and control returns to the caller. Resume with
    Command(resume=approval_decisions).

    Returns a delta that gets merged into state on resume.
    """
    from langgraph.types import interrupt

    deps = runner._deps
    if state.get("run_reason"):
        return {}
    if not state.get("messages"):
        return {"pending_tool_messages": []}

    last_message = state["messages"][-1]
    tool_calls = last_message.get("tool_calls") or []
    if not tool_calls:
        return {"pending_tool_messages": []}

    pending_approvals = []
    for tool_call in tool_calls:
        tool_call_id = str(tool_call.get("id", ""))
        function = tool_call.get("function", {})
        tool_name = str(function.get("name", ""))
        arguments_str = function.get("arguments", "{}")
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}

        decision = deps.evaluate_permission(tool_name, arguments)
        if not decision.allowed:
            continue
        if not decision.requires_approval or runner._auto_approve:
            continue

        pending_approvals.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )

    if not pending_approvals:
        return {"pending_tool_messages": []}

    # Pause execution and wait for human input
    approval_result = interrupt(
        {
            "type": "tool_approval_request",
            "session_id": runner._session_id,
            "approvals": pending_approvals,
        }
    )

    # approval_result is the resume value from Command(resume=...)
    # Expected shape: {"approved": ["tool_call_id1", ...], "denied": ["tool_call_id2", ...]}
    if not isinstance(approval_result, dict):
        approval_result = {"approved": [], "denied": []}

    approved_ids = set(approval_result.get("approved", []))
    denied_ids = set(approval_result.get("denied", []))

    denied_messages = []
    for tool_call in tool_calls:
        tool_call_id = str(tool_call.get("id", ""))
        function = tool_call.get("function", {})
        tool_name = str(function.get("name", ""))

        if tool_call_id in denied_ids:
            denied_messages.append(
                runner._build_tool_message(
                    tool_call_id=tool_call_id,
                    content="User denied approval",
                )
            )
        elif tool_call_id not in approved_ids:
            # Not in either list — treat as denied
            denied_messages.append(
                runner._build_tool_message(
                    tool_call_id=tool_call_id,
                    content="User denied approval",
                )
            )

    return {"pending_tool_messages": denied_messages}


def build_interrupt_graph(
    *,
    state_graph_cls: Any,
    start: Any,
    end: Any,
    runner: Any,
    checkpointer: Any,
) -> Any:
    """Build a compiled graph using interrupt() for human approval.

    Graph structure:
    START -> agent -> route_after_agent -> {tools: tools, __end__: end, approval: interrupt_approval}
    approval (interrupt) -> route_after_approval -> {tools: tools, __end__: end}
    tools -> route_after_tools -> {agent: agent, __end__: end}
    """
    graph_builder = state_graph_cls(AgentGraphState)
    graph_builder.add_node("agent", runner.agent_node)
    graph_builder.add_node("approval", lambda state: interrupt_approval_node(runner, state))
    graph_builder.add_node("tools", runner.tools_node)
    graph_builder.add_edge(start, "agent")
    graph_builder.add_conditional_edges(
        "agent",
        runner.route_after_agent,
        {"approval": "approval", "tools": "tools", "__end__": end},
    )
    graph_builder.add_conditional_edges(
        "approval",
        runner.route_after_approval,
        {"tools": "tools", "__end__": end},
    )
    graph_builder.add_conditional_edges(
        "tools",
        runner.route_after_tools,
        {"agent": "agent", "__end__": end},
    )
    return graph_builder.compile(checkpointer=checkpointer)


def is_interrupted(state: Any) -> bool:
    """Check if a graph execution is waiting for human input."""
    if state is None:
        return False
    metadata = getattr(state, "metadata", {})
    if isinstance(metadata, dict):
        return metadata.get("source") == "interrupt"
    return False


def get_interrupt_payload(state: Any) -> dict[str, Any] | None:
    """Extract the interrupt payload from a paused graph state."""
    if state is None:
        return None
    tasks = getattr(state, "tasks", [])
    if not tasks:
        return None
    for task in tasks:
        interrupts = getattr(task, "interrupts", [])
        if interrupts:
            return interrupts[0]
    return None
