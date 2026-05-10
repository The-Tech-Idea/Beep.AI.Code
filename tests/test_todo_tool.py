"""Tests for the TodoWrite agent tool."""

from __future__ import annotations

import asyncio
import pytest

from beep.agent.planning import TodoList
from beep.agent.tools.todo_tool import TodoWriteTool


def _todo_payload(*items: tuple[str, str, str, str]) -> list[dict[str, str]]:
    return [
        {"id": id_, "content": content, "status": status, "priority": priority}
        for id_, content, status, priority in items
    ]


def test_todo_write_replaces_list() -> None:
    todo_list = TodoList()
    tool = TodoWriteTool(todo_list)

    asyncio.run(
        tool.execute(
            todos=_todo_payload(
                ("1", "Read files", "pending", "high"),
                ("2", "Make changes", "pending", "medium"),
            )
        )
    )

    assert len(todo_list) == 2
    assert todo_list.items[0].content == "Read files"

    # Replace with new list
    asyncio.run(
        tool.execute(
            todos=_todo_payload(
                ("1", "Read files", "completed", "high"),
                ("3", "Run tests", "pending", "high"),
            )
        )
    )

    assert len(todo_list) == 2
    assert "2" not in {item.id for item in todo_list.items}
    assert todo_list.items[0].id == "1"
    assert todo_list.items[0].status == "completed"


def test_todo_write_returns_summary() -> None:
    todo_list = TodoList()
    tool = TodoWriteTool(todo_list)

    result = asyncio.run(
        tool.execute(
            todos=_todo_payload(
                ("1", "Setup", "completed", "high"),
                ("2", "Implement", "pending", "medium"),
            )
        )
    )

    assert result.success is True
    assert "2 items" in result.output
    assert "[x] 1: Setup" in result.output
    assert "[ ] 2: Implement" in result.output


def test_todo_write_clears_list_on_empty() -> None:
    todo_list = TodoList()
    tool = TodoWriteTool(todo_list)

    asyncio.run(
        tool.execute(
            todos=_todo_payload(
                ("1", "Task", "pending", "medium"),
            )
        )
    )
    assert len(todo_list) == 1

    asyncio.run(tool.execute(todos=[]))
    assert len(todo_list) == 0


def test_todo_write_rejects_invalid_todos() -> None:
    todo_list = TodoList()
    tool = TodoWriteTool(todo_list)

    result = asyncio.run(tool.execute(todos="not a list"))
    assert result.success is False
    assert "array" in result.output.lower() or "array" in result.error.lower()


def test_todo_write_clear_returns_message() -> None:
    todo_list = TodoList()
    tool = TodoWriteTool(todo_list)

    result = asyncio.run(tool.execute(todos=[]))
    assert result.success is True
    assert "cleared" in result.output.lower()


def test_todo_write_priority_sorting() -> None:
    todo_list = TodoList()
    tool = TodoWriteTool(todo_list)

    asyncio.run(
        tool.execute(
            todos=_todo_payload(
                ("1", "Low priority", "pending", "low"),
                ("2", "High priority", "pending", "high"),
                ("3", "Medium priority", "pending", "medium"),
            )
        )
    )

    ids = [item.id for item in todo_list.items]
    assert ids == ["2", "3", "1"]


def test_todo_write_progress_summary() -> None:
    todo_list = TodoList()
    tool = TodoWriteTool(todo_list)

    result = asyncio.run(
        tool.execute(
            todos=_todo_payload(
                ("1", "Done", "completed", "high"),
                ("2", "Pending", "pending", "medium"),
                ("3", "Also done", "completed", "low"),
            )
        )
    )

    assert "2/3 completed" in result.output
