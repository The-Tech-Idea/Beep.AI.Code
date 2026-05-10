"""Tool-execution step handlers for the autonomous agent graph runner."""

from __future__ import annotations

import json
from typing import Any

from beep.agent.graph_runner_limits import (
    check_per_step_limit,
    check_repeated_calls,
    check_total_limit,
)
from beep.agent.graph_support import AgentGraphState
from beep.agent.tools.base import ToolResult
from beep.errors.classifier import classify_error
from beep.errors.models import ErrorCategory


def tool_result_from_message(*, tool_name: str, content: Any) -> ToolResult:
    if content is None:
        return ToolResult(success=True, output="")
    if isinstance(content, str):
        raw_content = content
    elif isinstance(content, (dict, list)):
        raw_content = json.dumps(content)
    else:
        raw_content = str(content)

    try:
        payload = json.loads(raw_content)
    except (TypeError, json.JSONDecodeError):
        return ToolResult(success=True, output=raw_content)

    if (
        isinstance(payload, dict)
        and payload.get("tool_name") == tool_name
        and payload.get("is_error") is True
    ):
        return ToolResult(
            success=False,
            output=str(payload.get("output") or ""),
            error=str(payload.get("error") or f"{tool_name} failed"),
            is_error=True,
        )
    return ToolResult(success=True, output=raw_content)


def _build_structured_error(
    tool_name: str,
    result: ToolResult,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Create a serializable structured error dict from a ToolResult."""
    command = arguments.get("command") or arguments.get("shell_command")
    file_path = arguments.get("file_path") or arguments.get("path")
    classified = classify_error(
        tool_name,
        result.error or result.output,
        command=command,
        file_path=file_path,
        stdout=result.output or None,
        stderr=result.error or None,
    )
    return {
        "tool_name": classified.tool_name,
        "error_type": classified.error_type.value,
        "message": classified.message,
        "command": classified.command,
        "file_path": classified.file_path,
        "line": classified.line,
        "column": classified.column,
        "exit_code": classified.exit_code,
        "retryable": classified.retryable,
        "suggested_action": classified.suggested_action,
    }


def _handle_unknown_tool(
    runner: Any,
    state: AgentGraphState,
    tool_call_id: str,
    tool_name: str,
    step: int,
    tool_messages_by_id: dict[str, dict[str, Any]],
) -> None:
    error_dict = {
        "tool_name": tool_name,
        "error_type": ErrorCategory.UNKNOWN_TOOL.value,
        "message": f"Unknown tool: {tool_name}",
        "retryable": False,
        "suggested_action": "Use a valid tool from the available tool list.",
    }
    state["recent_errors"].append(error_dict)
    result = ToolResult(success=False, output="", error=f"Unknown tool: {tool_name}")
    tool_messages_by_id[tool_call_id] = runner._build_tool_message(
        tool_call_id=tool_call_id,
        content=result.error or "",
    )
    state["tool_calls_executed"] += 1
    runner._deps.format_tool_result(tool_name, result, step)
    runner._deps.log_event(
        "agent.tool.result",
        step=step,
        tool_name=tool_name,
        success=result.success,
    )


def _handle_invalid_arguments(
    runner: Any,
    state: AgentGraphState,
    tool_call_id: str,
    tool_name: str,
    arguments: Any,
    step: int,
    tool_messages_by_id: dict[str, dict[str, Any]],
) -> None:
    bad_type = type(arguments).__name__
    err_msg = (
        f"Invalid arguments for {tool_name}: expected a JSON object but received {bad_type}. "
        "Pass arguments as a JSON object."
    )
    error_dict = {
        "tool_name": tool_name,
        "error_type": ErrorCategory.INVALID_ARGUMENTS.value,
        "message": err_msg,
        "retryable": True,
        "suggested_action": "Pass arguments as a JSON object with the correct keys.",
    }
    state["recent_errors"].append(error_dict)
    result = ToolResult(
        success=False,
        output="",
        error=err_msg,
    )
    tool_messages_by_id[tool_call_id] = runner._build_tool_message(
        tool_call_id=tool_call_id,
        content=result.error or "",
    )
    state["tool_calls_executed"] += 1
    runner._deps.format_tool_result(tool_name, result, step)
    runner._deps.log_event(
        "agent.tool.result",
        step=step,
        tool_name=tool_name,
        success=result.success,
    )


async def _run_auto_verification(
    runner: Any,
    state: AgentGraphState,
    messages: list[dict[str, Any]],
    ordered_tool_messages: list[dict[str, Any]],
    executable_call_data: dict[str, tuple[str, dict[str, Any]]],
) -> None:
    if not getattr(runner, "_auto_verify", False):
        return
    successful_ids = set()
    for m in ordered_tool_messages:
        content = m.get("content", "")
        tool_call_id = str(m.get("tool_call_id", ""))
        actual_tool_name, _ = executable_call_data.get(tool_call_id, ("", {}))
        if tool_result_from_message(tool_name=actual_tool_name, content=content).success:
            successful_ids.add(tool_call_id)
    mutated_tools = [
        tname
        for tid, (tname, _) in executable_call_data.items()
        if tid in successful_ids and tname in runner._deps.file_touch_tools
    ]
    if not mutated_tools:
        return
    files_touched = state.get("files_touched", [])
    if not files_touched:
        return
    try:
        from beep.agent.verification import VerificationRunner

        vr = VerificationRunner(runner._workspace_root)
        verification_result = await vr.run(files_touched)
        verification_message = runner._build_tool_message(
            tool_call_id="__verification__",
            content=verification_result.to_message(),
        )
        runner._deps.console.print(
            f"[{'green' if verification_result.passed else 'red'}]"
            f"Verification: {'PASS' if verification_result.passed else 'FAIL'}"
            f"[/]"
        )
        runner._deps.log_event(
            "agent.verification.result",
            passed=verification_result.passed,
            files_checked=len(files_touched),
        )
        messages.append(verification_message)
    except Exception as exc:
        runner._deps.console.print(f"[yellow]Verification skipped: {exc}[/yellow]")
        runner._deps.log_event("agent.verification.error", error=str(exc))


async def tools_node(runner: Any, state: AgentGraphState) -> AgentGraphState:
    deps = runner._deps
    if state["run_reason"]:
        return state
    if not state["messages"]:
        return state
    last_message = state["messages"][-1]
    tool_calls = last_message.get("tool_calls") or []
    if not tool_calls:
        return state

    step = state["steps_executed"]
    step_any_success = False
    stop_reason: str | None = None
    messages = list(state["messages"])
    raw_tool_names = {tool.name for tool in runner._tools}
    pending_tool_messages = list(state["pending_tool_messages"])
    pending_tool_message_ids = {
        str(message.get("tool_call_id", ""))
        for message in pending_tool_messages
        if isinstance(message, dict)
    }
    state["pending_tool_messages"] = []
    state["recent_errors"] = []
    tool_messages_by_id: dict[str, dict[str, Any]] = {
        str(message.get("tool_call_id", "")): message
        for message in pending_tool_messages
        if isinstance(message, dict)
    }
    executable_tool_calls: list[dict[str, Any]] = []
    executable_call_data: dict[str, tuple[str, dict[str, Any]]] = {}

    for tool_index, tool_call in enumerate(tool_calls):
        tool_call_id = str(tool_call.get("id", ""))
        if check_per_step_limit(runner, state, tool_calls, tool_index, tool_messages_by_id, step):
            break

        if check_total_limit(runner, state, tool_calls, tool_index, tool_messages_by_id, step):
            stop_reason = "tool_call_total_limit"
            break

        function = tool_call.get("function", {})
        tool_name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")

        if check_repeated_calls(
            runner,
            state,
            tool_calls,
            tool_index,
            tool_name,
            arguments_str,
            tool_messages_by_id,
            step,
        ):
            stop_reason = "repeated_tool_calls"
            break

        if tool_call_id in pending_tool_message_ids:
            continue

        if tool_name not in raw_tool_names:
            _handle_unknown_tool(runner, state, tool_call_id, tool_name, step, tool_messages_by_id)
            continue

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}

        if not isinstance(arguments, dict):
            _handle_invalid_arguments(
                runner,
                state,
                tool_call_id,
                tool_name,
                arguments,
                step,
                tool_messages_by_id,
            )
            continue

        executable_tool_calls.append(tool_call)
        executable_call_data[tool_call_id] = (tool_name, arguments)

    if executable_tool_calls:
        for tool_call in executable_tool_calls:
            function = tool_call.get("function", {})
            tool_name = str(function.get("name", ""))
            arguments_str = str(function.get("arguments", "{}"))
            deps.console.print(f"[cyan]Calling: {tool_name}({arguments_str})[/cyan]")

        tool_node_messages = await runner._invoke_tool_node(
            [
                *messages[:-1],
                {**last_message, "tool_calls": executable_tool_calls},
            ]
        )
        state["tool_calls_executed"] += len(executable_tool_calls)

        for tool_message in tool_node_messages:
            if not isinstance(tool_message, dict):
                continue
            tool_call_id = str(tool_message.get("tool_call_id", ""))
            tool_messages_by_id[tool_call_id] = tool_message
            tool_name, arguments = executable_call_data.get(tool_call_id, ("", {}))
            result = tool_result_from_message(
                tool_name=tool_name,
                content=tool_message.get("content", ""),
            )
            if result.success:
                step_any_success = True
                if tool_name in deps.file_touch_tools:
                    touched_path = (
                        arguments.get("file_path")
                        or arguments.get("path")
                        or arguments.get("directory", "")
                    )
                    if touched_path:
                        runner._update_files_touched(state, str(touched_path))
            else:
                error_dict = _build_structured_error(tool_name, result, arguments)
                state["recent_errors"].append(error_dict)
                structured_content = result.output or ""
                if error_dict.get("suggested_action"):
                    structured_content += f"\n\nSuggested action: {error_dict['suggested_action']}"
                tool_messages_by_id[tool_call_id] = runner._build_tool_message(
                    tool_call_id=tool_call_id,
                    content=structured_content,
                )
            deps.format_tool_result(tool_name, result, step)
            deps.log_event(
                "agent.tool.result",
                step=step,
                tool_name=tool_name,
                success=result.success,
            )

    ordered_tool_messages = []
    for tool_call in tool_calls:
        tool_call_id = str(tool_call.get("id", ""))
        tool_message = tool_messages_by_id.get(tool_call_id)
        if tool_message is not None:
            ordered_tool_messages.append(tool_message)

    if ordered_tool_messages:
        messages.extend(ordered_tool_messages)

    state["messages"] = messages
    if stop_reason:
        state["run_reason"] = stop_reason
        return state

    await _run_auto_verification(
        runner, state, messages, ordered_tool_messages, executable_call_data
    )

    state["messages"] = messages
    if step_any_success:
        state["consecutive_failure_steps"] = 0
        return state

    state["consecutive_failure_steps"] += 1
    if state["consecutive_failure_steps"] >= runner._max_consecutive_failures:
        deps.console.print(
            f"[yellow]No progress: {runner._max_consecutive_failures} consecutive steps with all tool calls failing. "
            "Stopping agent.[/yellow]"
        )
        deps.log_event(
            "agent.run.no_progress",
            step=step,
            consecutive_failures=state["consecutive_failure_steps"],
        )
        state["run_reason"] = "no_progress"
    return state
