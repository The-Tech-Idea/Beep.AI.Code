"""TodoWrite tool for the autonomous coding agent.

Mirrors Claude Code's TodoWrite: the agent sends the complete list
of TODOs on each call, replacing whatever was there before.
"""

from __future__ import annotations

from typing import Any

from beep.agent.planning import TodoList
from beep.agent.tools.base import BaseTool, ToolResult


class TodoWriteTool(BaseTool):
    """Create or update the agent's TODO list.

    The agent must provide the complete list on each call. Partial updates
    are not supported — the full desired state is sent every time.
    """

    read_only_safe = True

    def __init__(self, todo_list: TodoList) -> None:
        self._todo_list = todo_list

    @property
    def name(self) -> str:
        return "todo_write"

    @property
    def description(self) -> str:
        return (
            "Create or update the TODO list for the current task. "
            "You MUST provide the COMPLETE list every time — the previous list is replaced. "
            "Use this to track multi-step work and show progress to the user. "
            "Statuses: pending, in_progress, completed, cancelled. "
            "Priorities: low, medium, high."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "todos": {
                "type": "array",
                "description": "Complete list of TODO items to replace the current list",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique identifier for this TODO (e.g. '1', '2')",
                        },
                        "content": {
                            "type": "string",
                            "description": "The task description",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                            "description": "Current status of the TODO",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Priority level",
                        },
                    },
                    "required": ["id", "content"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        todos_raw = kwargs.get("todos", [])
        if not isinstance(todos_raw, list):
            return ToolResult(
                success=False,
                output="",
                error="todos must be an array of objects",
            )

        self._todo_list.replace(todos_raw)
        return ToolResult(
            success=True,
            output=self._format_summary(),
        )

    def _format_summary(self) -> str:
        if not self._todo_list:
            return "TODO list cleared."

        lines = [f"TODO list ({len(self._todo_list)} items):"]
        for item in self._todo_list.items:
            status_icon = {
                "pending": "[ ]",
                "in_progress": "[~]",
                "completed": "[x]",
                "cancelled": "[-]",
            }.get(item.status, "[ ]")
            lines.append(f"  {status_icon} {item.id}: {item.content}")

        completed = self._todo_list.completed_count
        total = len(self._todo_list)
        lines.append(f"\nProgress: {completed}/{total} completed")
        return "\n".join(lines)
