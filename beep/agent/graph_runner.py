"""Runner nodes for the LangGraph-backed autonomous agent runtime."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from beep.agent.backends import AgentModelBackend
from beep.agent.graph_runner_display import emit_summary, render_todo
from beep.agent.graph_runner_steps import agent_node as _agent_node
from beep.agent.graph_runner_steps import approval_node as _approval_node
from beep.agent.graph_runner_steps import tools_node as _tools_node
from beep.agent.graph_runtime_deps_factory import make_graph_runtime_dependencies
from beep.agent.graph_runtime_dependencies import GraphRuntimeDependencies
from beep.agent.graph_support import AgentGraphState
from beep.agent.planning import TodoList
from beep.agent.tools.base import BaseTool
from beep.permissions.manager import (
    PermissionDecision,
    PermissionManager,
    SandboxMode,
    coerce_sandbox_mode,
)
from beep.rules.loader import LoadedRule


InitialUserContent = str | dict[str, Any] | list[dict[str, Any]]


def _coerce_initial_user_blocks(value: InitialUserContent) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [dict(value)]
    if isinstance(value, list):
        blocks: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise TypeError(
                    "initial_user_content list items must be dict content blocks; "
                    f"item {index} was {type(item).__name__}."
                )
            blocks.append(dict(item))
        return blocks
    raise TypeError(
        "initial_user_content must be a string, one content block dict, or a list of content block dicts."
    )


def _resolve_explicit_approval_policy(tools: list[BaseTool]) -> bool | None:
    explicit_values: list[bool] = []
    for tool in tools:
        explicit_value = getattr(tool, "requires_human_approval", None)
        if isinstance(explicit_value, bool):
            explicit_values.append(explicit_value)
    if not explicit_values:
        return None
    if any(explicit_values):
        return True
    return False


def _known_permission_tool(
    tools: list[BaseTool], manager: PermissionManager, tool_name: str
) -> bool:
    return manager.has_rule(tool_name) and any(tool.name == tool_name for tool in tools)


def _attach_tool_approval_policies(
    deps: GraphRuntimeDependencies,
    tools: list[BaseTool],
    workspace_root: Path,
    sandbox_mode: SandboxMode | str | bool | None,
) -> GraphRuntimeDependencies:
    tools_by_name: dict[str, list[BaseTool]] = {}
    for tool in tools:
        tools_by_name.setdefault(tool.name, []).append(tool)

    from beep.app_service import get_app_service

    permission_manager = get_app_service().permissions
    effective_sandbox_mode = coerce_sandbox_mode(sandbox_mode)

    def _evaluate_permission(tool_name: str, arguments: dict[str, Any]) -> PermissionDecision:
        matching_tools = tools_by_name.get(tool_name, [])
        if _known_permission_tool(matching_tools, permission_manager, tool_name):
            return permission_manager.evaluate_permission(
                tool_name,
                arguments,
                workspace_root,
                sandbox_mode=effective_sandbox_mode,
            )

        explicit_policy = _resolve_explicit_approval_policy(matching_tools)
        if explicit_policy is not None:
            return PermissionDecision(
                True,
                explicit_policy,
                "Requires approval" if explicit_policy else "Auto-approved",
            )
        return deps.evaluate_permission(tool_name, arguments)

    def _requires_approval(tool_name: str, arguments: dict[str, Any]) -> bool:
        return _evaluate_permission(tool_name, arguments).requires_approval

    return replace(
        deps, evaluate_permission=_evaluate_permission, requires_approval=_requires_approval
    )


class AgentGraphRunner:
    """Owns node behavior for the LangGraph-backed autonomous agent runtime."""

    def __init__(
        self,
        *,
        backend: AgentModelBackend,
        tools: list[BaseTool],
        workspace_root: Path,
        max_steps: int,
        max_tool_calls_per_step: int,
        max_tool_calls_total: int,
        step_timeout: float,
        max_repeated_calls: int,
        max_consecutive_failures: int,
        max_tool_output_chars: int,
        auto_approve: bool,
        sandbox_mode: SandboxMode | str | bool | None,
        system_prompt: str,
        workspace_rules: list[LoadedRule] | None,
        session_id: str,
        tool_node_cls: Any | None,
        runtime_deps: GraphRuntimeDependencies | None = None,
        todo_list: TodoList | None = None,
        auto_verify: bool = False,
    ) -> None:
        self._backend = backend
        self._tools = tools
        self._workspace_root = workspace_root
        self._max_steps = max_steps
        self._max_tool_calls_per_step = max(1, max_tool_calls_per_step)
        self._max_tool_calls_total = max(1, max_tool_calls_total)
        self._step_timeout = step_timeout
        self._max_repeated_calls = max(1, max_repeated_calls)
        self._max_consecutive_failures = max(1, max_consecutive_failures)
        self._max_tool_output_chars = max(500, max_tool_output_chars)
        self._auto_approve = auto_approve
        self._auto_verify = auto_verify
        self._system_prompt = system_prompt
        self._workspace_rules = list(workspace_rules) if workspace_rules else []
        self._active_rules_context = ""
        self._session_id = session_id
        self._langgraph_tool_node: Any | None = None
        self._tool_node_cls = tool_node_cls
        self._todo_list = todo_list or TodoList()
        self._parallel = True
        self._provider_options: dict[str, Any] | None = None
        self._response_format: dict[str, Any] | None = None
        self._stream_emitter: Any | None = None
        self._deps = _attach_tool_approval_policies(
            runtime_deps or make_graph_runtime_dependencies(),
            self._tools,
            self._workspace_root,
            sandbox_mode,
        )

    def set_provider_options(self, provider_options: dict[str, Any] | None) -> None:
        self._provider_options = dict(provider_options) if provider_options else None

    def set_response_format(self, response_format: dict[str, Any] | None) -> None:
        self._response_format = dict(response_format) if response_format else None

    def set_stream_emitter(self, emitter: Any | None) -> None:
        self._stream_emitter = emitter

    def build_initial_user_message(
        self,
        goal: str,
        *,
        initial_user_content: InitialUserContent | None = None,
    ) -> dict[str, Any]:
        goal_prompt = (
            f"Achieve this goal: {goal}\n\n"
            "You have access to tools. Use them step by step. "
            "When done, respond with a summary of what was accomplished."
        )
        if initial_user_content is None:
            content: Any = goal_prompt
        elif isinstance(initial_user_content, str):
            extra_text = initial_user_content.strip()
            content = (
                goal_prompt
                if not extra_text
                else f"{goal_prompt}\n\nAdditional user input:\n{initial_user_content}"
            )
        else:
            blocks = _coerce_initial_user_blocks(initial_user_content)
            content = goal_prompt if not blocks else [{"type": "text", "text": goal_prompt}, *blocks]
        return {"role": "user", "content": content}

    def build_initial_state(
        self,
        goal: str,
        *,
        initial_user_content: InitialUserContent | None = None,
    ) -> AgentGraphState:
        return {
            "schema_version": "2.0",
            "messages": [
                {"role": "system", "content": self._system_prompt},
                self.build_initial_user_message(goal, initial_user_content=initial_user_content),
            ],
            "steps_executed": 0,
            "tool_calls_executed": 0,
            "files_touched": [],
            "run_reason": None,
            "final_message": None,
            "consecutive_failure_steps": 0,
            "tool_call_hashes": {},
            "per_step_limit_hit": False,
            "total_limit_hit": False,
            "pending_tool_messages": [],
            "recent_errors": [],
            "max_retries": 3,
            "error_count": 0,
            "todo_list": self._todo_list.to_dict(),
        }

    def _sync_todo_to_state(self, state: AgentGraphState) -> None:
        state["todo_list"] = self._todo_list.to_dict()

    def _restore_todo_from_state(self, state: AgentGraphState) -> None:
        """Restore internal TodoList from persisted checkpoint state."""
        persisted = state.get("todo_list", {})
        if persisted and not self._todo_list:
            self._todo_list = TodoList.from_dict(persisted)

    def _render_todo(self, state: AgentGraphState) -> None:
        render_todo(self._todo_list, state, self._deps.console)

    def emit_summary(self, state: AgentGraphState) -> None:
        emit_summary(state, self._deps.console, self._deps.log_event)

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self._tools]

    def _normalize_agent_message(self, message: dict[str, Any]) -> dict[str, Any]:
        return self._deps.langchain_message_to_agent_dict(
            self._deps.agent_dict_to_langchain_message(message)
        )

    def _build_tool_message(self, *, tool_call_id: str, content: str) -> dict[str, Any]:
        return self._deps.langchain_message_to_agent_dict(
            self._deps.tool_result_to_langchain_message(tool_call_id=tool_call_id, content=content)
        )

    def _get_langgraph_tool_node(self) -> Any:
        if self._langgraph_tool_node is None:
            if self._tool_node_cls is None:
                raise RuntimeError("LangGraph ToolNode is not configured for the agent runtime.")
            self._langgraph_tool_node = self._tool_node_cls(
                self._deps.adapt_tools(
                    self._tools,
                    max_output_chars=self._max_tool_output_chars,
                    require_human_approval=False,
                )
            )
        return self._langgraph_tool_node

    def _update_files_touched(self, state: AgentGraphState, file_path: str) -> None:
        if not file_path or file_path in state["files_touched"]:
            return
        state["files_touched"] = [*state["files_touched"], file_path]
        if not self._workspace_rules:
            return
        from beep.rules.resolver import build_rules_context, resolve_rules_for_paths

        new_context = build_rules_context(
            resolve_rules_for_paths(self._workspace_rules, state["files_touched"])
        )
        if new_context and new_context != self._active_rules_context:
            self._active_rules_context = new_context
            system_msg_index = None
            for idx, msg in enumerate(state["messages"]):
                if isinstance(msg, dict) and msg.get("role") == "system":
                    system_msg_index = idx
                    break
            if system_msg_index is not None:
                sys_content = state["messages"][system_msg_index]["content"]
                if new_context not in sys_content:
                    state["messages"][system_msg_index] = {
                        "role": "system",
                        "content": sys_content + "\n\n" + new_context,
                    }

    async def _invoke_tool_node(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tool_node = self._get_langgraph_tool_node()
        langchain_messages = self._deps.agent_messages_to_langchain_messages(messages)
        last_message = messages[-1] if messages else {}
        tool_calls = last_message.get("tool_calls", [])

        if self._parallel and len(tool_calls) > 1:
            from beep.agent.parallel import execute_parallel_batch

            tool_messages = await execute_parallel_batch(
                tool_calls=tool_calls,
                tool_node=tool_node,
                messages=langchain_messages,
            )
        else:
            result = await tool_node.ainvoke({"messages": langchain_messages})
            tool_messages = result.get("messages") if isinstance(result, dict) else []

        if not isinstance(tool_messages, list):
            raise RuntimeError("LangGraph ToolNode returned an unexpected result shape.")
        return self._deps.langchain_messages_to_agent_dicts(tool_messages)

    async def agent_node(self, state: AgentGraphState) -> AgentGraphState:
        return await _agent_node(self, state)

    async def approval_node(self, state: AgentGraphState) -> AgentGraphState:
        return await _approval_node(self, state)

    async def tools_node(self, state: AgentGraphState) -> AgentGraphState:
        return await _tools_node(self, state)

    def route_after_agent(self, state: AgentGraphState) -> str:
        if state["run_reason"]:
            return "__end__"
        last_message = state["messages"][-1] if state["messages"] else {}
        if last_message.get("role") == "assistant" and last_message.get("tool_calls"):
            return "approval"
        return "__end__"

    def route_after_approval(self, state: AgentGraphState) -> str:
        if state["run_reason"]:
            return "__end__"
        last_message = state["messages"][-1] if state["messages"] else {}
        if last_message.get("role") == "assistant" and last_message.get("tool_calls"):
            return "tools"
        return "__end__"

    def route_after_tools(self, state: AgentGraphState) -> str:
        if state["run_reason"]:
            return "__end__"
        return "agent"
