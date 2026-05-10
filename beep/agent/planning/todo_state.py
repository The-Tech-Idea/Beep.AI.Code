"""TODO list state manager for the autonomous agent runtime."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TodoItem:
    """A single TODO entry in the agent's task list."""

    id: str
    content: str
    status: str = "pending"
    priority: str = "medium"

    def __post_init__(self) -> None:
        valid_statuses = {"pending", "in_progress", "completed", "cancelled"}
        valid_priorities = {"low", "medium", "high"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of {valid_statuses}")
        if self.priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority '{self.priority}'. Must be one of {valid_priorities}"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "TodoItem":
        return cls(
            id=data["id"],
            content=data["content"],
            status=data.get("status", "pending"),
            priority=data.get("priority", "medium"),
        )


class TodoList:
    """Mutable TODO list with atomic replace semantics.

    The agent replaces the entire list on each TodoWrite call
    (matching Claude Code's behavior). No partial updates.
    """

    def __init__(self) -> None:
        self._items: dict[str, TodoItem] = {}

    @property
    def items(self) -> list[TodoItem]:
        return sorted(
            self._items.values(),
            key=lambda item: (
                {"high": 0, "medium": 1, "low": 2}.get(item.priority, 3),
                item.id,
            ),
        )

    @property
    def pending_count(self) -> int:
        return sum(1 for item in self._items.values() if item.status == "pending")

    @property
    def completed_count(self) -> int:
        return sum(1 for item in self._items.values() if item.status == "completed")

    def replace(self, items: list[dict[str, str]]) -> None:
        """Replace the entire TODO list atomically.

        This is the primary API used by TodoWriteTool — the agent
        sends the full list on each call. The partial-update methods
        below are available for internal bookkeeping.
        """
        self._items.clear()
        for item_data in items:
            item = TodoItem.from_dict(item_data)
            self._items[item.id] = item

    def mark_completed(self, todo_id: str) -> bool:
        """Mark a single TODO as completed. Returns True if found."""
        if todo_id in self._items:
            current = self._items[todo_id]
            self._items[todo_id] = TodoItem(
                id=current.id,
                content=current.content,
                status="completed",
                priority=current.priority,
            )
            return True
        return False

    def clear(self) -> None:
        self._items.clear()

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {item_id: item.to_dict() for item_id, item in self._items.items()}

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, str]]) -> "TodoList":
        todo_list = cls()
        todo_list._items = {
            item_id: TodoItem.from_dict(item_data) for item_id, item_data in data.items()
        }
        return todo_list

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)
