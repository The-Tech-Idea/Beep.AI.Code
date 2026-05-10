"""Sub-agent dispatcher for spawning isolated agent instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool

VALID_SUBAGENT_TYPES = frozenset({"explore", "plan", "general"})


@dataclass
class SubAgentResult:
    """Result from a completed sub-agent run."""

    subagent_type: str
    goal: str
    summary: str
    steps_executed: int
    success: bool
    _dispatcher: Any = field(default=None, repr=False, compare=False)
    _tools: list[BaseTool] = field(default_factory=list, repr=False, compare=False)
    _backend: Any = field(default=None, repr=False, compare=False)
    _system_prompt: str = field(default="", repr=False, compare=False)
    _session_id: str = field(default="", repr=False, compare=False)

    @property
    def tool_count(self) -> int:
        return len(self._tools)


class SubAgentDispatcher:
    """Spawns sub-agents with isolated context and scoped tools.

    Sub-agents run in their own context window. The parent agent
    receives only the summary, keeping its context clean.

    Depth is limited to 1 — sub-agents cannot spawn their own
    sub-agents (prevents recursive explosion).
    """

    def __init__(
        self,
        *,
        workspace_root: Path,
        all_tools: list[BaseTool],
        max_subagent_steps: int = 10,
        current_depth: int = 0,
        max_depth: int = 1,
    ) -> None:
        self._workspace_root = workspace_root
        self._all_tools = all_tools
        self._max_subagent_steps = max_subagent_steps
        self._current_depth = current_depth
        self._max_depth = max_depth

    def get_tool_subset(self, subagent_type: str) -> list[BaseTool]:
        """Return the tool subset for a given sub-agent type."""
        from beep.agent.subagents.explore_agent import EXPLORE_TOOLS
        from beep.agent.subagents.plan_agent import PLAN_TOOLS

        allowed_names: frozenset[str]
        if subagent_type == "explore":
            allowed_names = EXPLORE_TOOLS
        elif subagent_type == "plan":
            allowed_names = PLAN_TOOLS
        else:
            allowed_names = frozenset(t.name for t in self._all_tools)

        return [t for t in self._all_tools if t.name in allowed_names]

    def can_spawn(self) -> bool:
        return self._current_depth < self._max_depth

    def prepare_dispatch(
        self,
        *,
        goal: str,
        subagent_type: str,
        backend: Any,
        system_prompt: str,
        session_id: str,
    ) -> SubAgentResult:
        """Prepare a sub-agent dispatch. Returns a SubAgentResult with metadata.

        The caller is responsible for executing the actual async run.
        """
        if not self.can_spawn():
            return SubAgentResult(
                subagent_type=subagent_type,
                goal=goal,
                summary="Error: Cannot spawn sub-agent — maximum depth reached.",
                steps_executed=0,
                success=False,
            )

        if subagent_type not in VALID_SUBAGENT_TYPES:
            return SubAgentResult(
                subagent_type=subagent_type,
                goal=goal,
                summary=f"Error: Unknown sub-agent type '{subagent_type}'. Valid types: {', '.join(sorted(VALID_SUBAGENT_TYPES))}.",
                steps_executed=0,
                success=False,
            )

        tools = self.get_tool_subset(subagent_type)
        child_dispatcher = SubAgentDispatcher(
            workspace_root=self._workspace_root,
            all_tools=tools,
            max_subagent_steps=self._max_subagent_steps,
            current_depth=self._current_depth + 1,
            max_depth=self._max_depth,
        )

        return SubAgentResult(
            subagent_type=subagent_type,
            goal=goal,
            summary="",
            steps_executed=0,
            success=True,
            _dispatcher=child_dispatcher,
            _tools=tools,
            _backend=backend,
            _system_prompt=system_prompt,
            _session_id=session_id,
        )
