"""Tests for the TODO list state manager."""

from __future__ import annotations

import pytest

from beep.agent.planning import TodoItem, TodoList


def _make_item(
    item_id: str, content: str = "", status: str = "pending", priority: str = "medium"
) -> dict[str, str]:
    return {
        "id": item_id,
        "content": content or f"Task {item_id}",
        "status": status,
        "priority": priority,
    }


class TestTodoItem:
    def test_default_values(self) -> None:
        item = TodoItem(id="1", content="test")
        assert item.status == "pending"
        assert item.priority == "medium"

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            TodoItem(id="1", content="test", status="invalid")

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid priority"):
            TodoItem(id="1", content="test", priority="invalid")

    def test_to_dict_roundtrip(self) -> None:
        item = TodoItem(id="1", content="test", status="in_progress", priority="high")
        data = item.to_dict()
        restored = TodoItem.from_dict(data)
        assert restored == item

    def test_valid_statuses(self) -> None:
        for status in ("pending", "in_progress", "completed", "cancelled"):
            item = TodoItem(id="1", content="test", status=status)
            assert item.status == status

    def test_valid_priorities(self) -> None:
        for priority in ("low", "medium", "high"):
            item = TodoItem(id="1", content="test", priority=priority)
            assert item.priority == priority


class TestTodoList:
    def test_initially_empty(self) -> None:
        todo = TodoList()
        assert len(todo) == 0
        assert not todo
        assert todo.pending_count == 0
        assert todo.completed_count == 0

    def test_replace_adds_items(self) -> None:
        todo = TodoList()
        todo.replace([_make_item("1"), _make_item("2"), _make_item("3")])
        assert len(todo) == 3

    def test_replace_clears_previous(self) -> None:
        todo = TodoList()
        todo.replace([_make_item("1")])
        todo.replace([_make_item("2")])
        assert len(todo) == 1
        assert "1" not in {item.id for item in todo.items}

    def test_replace_accepts_dicts(self) -> None:
        todo = TodoList()
        todo.replace([{"id": "a", "content": "work", "status": "pending", "priority": "high"}])
        assert len(todo) == 1
        assert todo.items[0].content == "work"

    def test_mark_completed(self) -> None:
        todo = TodoList()
        todo.replace([_make_item("1"), _make_item("2")])
        assert todo.completed_count == 0
        assert todo.mark_completed("1") is True
        assert todo.completed_count == 1
        assert todo.pending_count == 1

    def test_mark_completed_missing_id(self) -> None:
        todo = TodoList()
        assert todo.mark_completed("nonexistent") is False

    def test_clear(self) -> None:
        todo = TodoList()
        todo.replace([_make_item("1"), _make_item("2")])
        todo.clear()
        assert len(todo) == 0

    def test_items_sorted_by_priority(self) -> None:
        todo = TodoList()
        todo.replace(
            [
                _make_item("low", priority="low"),
                _make_item("high", priority="high"),
                _make_item("med", priority="medium"),
            ]
        )
        ids = [item.id for item in todo.items]
        assert ids == ["high", "med", "low"]

    def test_to_dict_roundtrip(self) -> None:
        todo = TodoList()
        todo.replace([_make_item("1"), _make_item("2", status="completed")])
        data = todo.to_dict()
        restored = TodoList.from_dict(data)
        assert len(restored) == 2
        assert restored.completed_count == 1

    def test_bool_false_when_empty(self) -> None:
        assert not TodoList()

    def test_bool_true_when_nonempty(self) -> None:
        todo = TodoList()
        todo.replace([_make_item("1")])
        assert bool(todo)
