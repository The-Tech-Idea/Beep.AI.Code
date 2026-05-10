"""Step handlers for the LangGraph-backed autonomous agent runner."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from beep.agent.backend_requests import (
    AgentCompletionRequest,
    complete_agent_completion_request,
    stream_agent_completion_request,
)
from beep.agent.backend_stream_support import CompletionStreamAccumulator
from beep.agent.context_manager import should_trim, trim_messages
from beep.agent.graph_support import AgentGraphState
from beep.agent.graph_runner_tool_support import tools_node as _tools_node_impl
from beep.errors.injector import format_error_injection


async def _run_streaming_completion(
    runner: Any,
    request: AgentCompletionRequest,
    *,
    step: int,
) -> Any:
    emitter = getattr(runner, "_stream_emitter", None)
    if emitter is None:
        return await complete_agent_completion_request(runner._backend, request)

    accumulator = CompletionStreamAccumulator()
    announced_tool_indexes: set[int] = set()
    async for delta in stream_agent_completion_request(runner._backend, request):
        accumulator.append(delta)
        if delta.content:
            emitter.response_chunk(delta.content, step=step)
        for tool_call in delta.tool_calls:
            if tool_call.name and tool_call.index not in announced_tool_indexes:
                emitter.tool_start(tool_call.name, step=step)
                announced_tool_indexes.add(tool_call.index)
    return accumulator.build_completion()


def _inject_structured_errors(state: AgentGraphState) -> None:
    """Append structured error context before the next agent turn."""
    recent = state.get("recent_errors", [])
    if not recent:
        return
    error_block = format_error_injection([_dict_to_structured_error(e) for e in recent])
    if error_block:
        state["messages"] = [
            *state["messages"],
            {"role": "user", "content": error_block},
        ]
    state["recent_errors"] = []


def _dict_to_structured_error(err: dict[str, Any]) -> Any:
    """Convert a serializable error dict back to a StructuredToolError for XML rendering."""
    from beep.errors.models import ErrorCategory, StructuredToolError

    error_type = ErrorCategory(err.get("error_type", "Unknown"))
    return StructuredToolError(
        tool_name=err["tool_name"],
        error_type=error_type,
        message=err.get("message", ""),
        command=err.get("command"),
        file_path=err.get("file_path"),
        line=err.get("line"),
        column=err.get("column"),
        exit_code=err.get("exit_code"),
        retryable=err.get("retryable", True),
        suggested_action=err.get("suggested_action"),
    )


async def agent_node(runner: Any, state: AgentGraphState) -> AgentGraphState:
    deps = runner._deps
    if state["run_reason"]:
        return state
    if state["steps_executed"] >= runner._max_steps:
        deps.console.print(f"\n[yellow]Reached max steps ({runner._max_steps})[/yellow]")
        deps.log_event("agent.run.max_steps", max_steps=runner._max_steps)
        state["run_reason"] = "max_steps"
        runner._sync_todo_to_state(state)
        return state

    if should_trim(state["messages"]):
        trimmed = trim_messages(state["messages"])
        if len(trimmed) < len(state["messages"]):
            deps.log_event(
                "agent.context.trimmed",
                original_count=len(state["messages"]),
                trimmed_count=len(trimmed),
            )
            state["messages"] = trimmed

    _inject_structured_errors(state)

    step = state["steps_executed"] + 1
    state["steps_executed"] = step
    deps.console.print(f"\n[dim]Step {step}/{runner._max_steps}[/dim]")
    runner._restore_todo_from_state(state)
    runner._render_todo(state)

    completion = None
    max_api_retries = 3
    request = AgentCompletionRequest(
        messages=state["messages"],
        tools=runner._get_tool_definitions(),
        stream=getattr(runner, "_stream_emitter", None) is not None,
        response_format=getattr(runner, "_response_format", None),
        provider_options=getattr(runner, "_provider_options", None),
    )
    for attempt in range(max_api_retries):
        try:
            completion = await asyncio.wait_for(
                _run_streaming_completion(runner, request, step=step),
                timeout=runner._step_timeout,
            )
            break
        except asyncio.TimeoutError:
            deps.console.print(
                f"[red]Step {step}: API call timed out after {runner._step_timeout}s[/red]"
            )
            deps.log_event("agent.run.timeout", step=step, timeout=runner._step_timeout)
            state["run_reason"] = "api_timeout"
            runner._sync_todo_to_state(state)
            return state
        except Exception as exc:
            if attempt < max_api_retries - 1:
                backoff = 2**attempt
                deps.console.print(
                    f"[yellow]Step {step}: API error (attempt {attempt + 1}/{max_api_retries}), "
                    f"retrying in {backoff}s: {exc}[/yellow]"
                )
                deps.log_event(
                    "agent.run.api_retry",
                    step=step,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                await asyncio.sleep(backoff)
                continue
            deps.console.print(f"[red]API error (all retries exhausted): {exc}[/red]")
            deps.log_event("agent.run.error", step=step, error=str(exc))
            state["run_reason"] = "api_error"
            runner._sync_todo_to_state(state)
            return state

    if completion is None:
        state["run_reason"] = "api_error"
        runner._sync_todo_to_state(state)
        return state

    content = completion.content
    tool_calls = completion.tool_calls
    if tool_calls:
        assistant_message: dict[str, Any] = {"role": "assistant", "tool_calls": tool_calls}
        if content:
            assistant_message["content"] = content
            if getattr(runner, "_stream_emitter", None) is None:
                deps.render_response(str(content), title="Agent")
        state["messages"] = [*state["messages"], runner._normalize_agent_message(assistant_message)]
        runner._sync_todo_to_state(state)
        return state

    if content:
        if getattr(runner, "_stream_emitter", None) is None:
            deps.render_response(str(content), title="Agent")
        assistant_message = runner._normalize_agent_message(
            {"role": "assistant", "content": content}
        )
        state["messages"] = [*state["messages"], assistant_message]
        deps.append_message(runner._session_id, assistant_message)
        state["run_reason"] = "completed"
        state["final_message"] = str(content)
        runner._sync_todo_to_state(state)
        return state

    deps.log_event("agent.run.empty_response", step=step)
    state["run_reason"] = "empty_response"
    runner._sync_todo_to_state(state)
    return state


async def approval_node(runner: Any, state: AgentGraphState) -> AgentGraphState:
    deps = runner._deps
    if state["run_reason"]:
        return state
    if not state["messages"]:
        state["pending_tool_messages"] = []
        return state

    last_message = state["messages"][-1]
    tool_calls = last_message.get("tool_calls") or []
    if not tool_calls:
        state["pending_tool_messages"] = []
        return state

    denied_messages: list[dict[str, Any]] = []
    step = state["steps_executed"]
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
            deps.log_event(
                "agent.tool.policy_denied",
                step=step,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                reason=decision.reason,
            )
            denied_messages.append(
                runner._build_tool_message(
                    tool_call_id=tool_call_id,
                    content=f"Blocked by sandbox policy: {decision.reason}",
                )
            )
            continue

        if not decision.requires_approval or runner._auto_approve:
            continue
        if deps.request_approval(tool_name, arguments):
            continue

        deps.log_event(
            "agent.tool.approval_denied",
            step=step,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        denied_messages.append(
            runner._build_tool_message(tool_call_id=tool_call_id, content="User denied approval")
        )

    state["pending_tool_messages"] = denied_messages
    return state


async def tools_node(runner: Any, state: AgentGraphState) -> AgentGraphState:
    return await _tools_node_impl(runner, state)
