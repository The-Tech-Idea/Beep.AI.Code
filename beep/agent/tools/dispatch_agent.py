"""DispatchAgent tool for spawning sub-agents."""

from __future__ import annotations

from typing import Any

from beep.agent.planning import TodoList
from beep.agent.subagents.dispatcher import SubAgentDispatcher
from beep.agent.subagents.result_formatter import format_subagent_result
from beep.agent.tools.base import BaseTool, ToolResult


class DispatchAgentTool(BaseTool):
    """Spawn a specialized sub-agent to handle a focused task.

    Sub-agents run in their own isolated context with scoped tools.
    Only the summary is returned to the parent agent, keeping its
    context window clean.

    Sub-agent types:
    - explore: Read-only codebase exploration
    - plan: Architecture and implementation planning
    - general: Full tool access (use sparingly)
    """

    read_only_safe = False

    def __init__(
        self,
        dispatcher: SubAgentDispatcher,
        *,
        backend: Any = None,
        system_prompt: str = "",
        session_id: str = "",
    ) -> None:
        self._dispatcher = dispatcher
        self._backend = backend
        self._system_prompt = system_prompt
        self._session_id = session_id

    @property
    def name(self) -> str:
        return "dispatch_agent"

    @property
    def description(self) -> str:
        return (
            "Spawn a specialized sub-agent for a focused task. "
            "Sub-agents run in isolated context with scoped tools. "
            "Types: explore (read-only codebase scan), plan (architecture planning), "
            "general (full tool access). "
            "Only the summary is returned to you — use this for exploration or planning."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "task": {
                "type": "string",
                "description": "The task or goal for the sub-agent",
            },
            "subagent_type": {
                "type": "string",
                "enum": ["explore", "plan", "general"],
                "description": "Type of sub-agent to spawn",
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        task = str(kwargs.get("task", ""))
        subagent_type = str(kwargs.get("subagent_type", "explore"))

        if not task:
            return ToolResult(
                success=False,
                output="",
                error="task is required — describe what the sub-agent should do",
            )

        if not self._dispatcher.can_spawn():
            return ToolResult(
                success=False,
                output="",
                error="Cannot spawn sub-agent: maximum nesting depth reached",
            )

        dispatch = self._dispatcher.prepare_dispatch(
            goal=task,
            subagent_type=subagent_type,
            backend=self._backend,
            system_prompt=self._system_prompt,
            session_id=self._session_id,
        )

        if not dispatch.success:
            return ToolResult(
                success=False,
                output="",
                error=dispatch.summary,
            )

        try:
            from beep.agent.graph import AgentGraphRunner
            from beep.agent.graph_support import (
                _build_compiled_graph,
                _checkpoint_path,
                _load_langgraph_dependencies,
            )

            start, end, state_graph_cls, async_sqlite_saver_cls, tool_node_cls = (
                _load_langgraph_dependencies()
            )
            session_id = f"{dispatch._session_id}:sub:{subagent_type}"
            todo_list = TodoList()

            runner = AgentGraphRunner(
                backend=dispatch._backend,
                tools=dispatch._tools,
                workspace_root=self._dispatcher._workspace_root,
                max_steps=self._dispatcher._max_subagent_steps,
                max_tool_calls_per_step=5,
                max_tool_calls_total=50,
                step_timeout=60.0,
                max_repeated_calls=3,
                max_consecutive_failures=3,
                max_tool_output_chars=10000,
                auto_approve=True,
                sandbox_mode="workspace_write",
                system_prompt=dispatch._system_prompt,
                workspace_rules=None,
                session_id=session_id,
                tool_node_cls=tool_node_cls,
                todo_list=todo_list,
            )

            initial_state = runner.build_initial_state(dispatch.goal)
            checkpoint_path = _checkpoint_path(self._dispatcher._workspace_root)
            config = {"configurable": {"thread_id": session_id}}

            async with async_sqlite_saver_cls.from_conn_string(
                str(checkpoint_path)
            ) as checkpointer:
                graph = _build_compiled_graph(
                    state_graph_cls=state_graph_cls,
                    start=start,
                    end=end,
                    runner=runner,
                    checkpointer=checkpointer,
                )
                final_state = await graph.ainvoke(initial_state, config=config)

            summary = format_subagent_result(
                name=subagent_type,
                goal=dispatch.goal,
                steps_executed=final_state.get("steps_executed", 0),
                final_message=final_state.get("final_message"),
                todo_list=final_state.get("todo_list"),
            )

            return ToolResult(
                success=True,
                output=summary,
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output="",
                error=f"Sub-agent execution failed: {exc}",
            )
