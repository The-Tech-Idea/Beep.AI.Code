"""Tests for the parallel tool execution module."""

from __future__ import annotations

import pytest

from beep.agent.parallel.batcher import batch_tool_calls
from beep.agent.parallel.classifier import is_read_only_tool
from beep.agent.parallel.executor import execute_parallel_batch


class TestClassifier:
    def test_read_only_tools(self) -> None:
        for name in ("file_read", "search", "glob_files", "list_directory", "context"):
            assert is_read_only_tool(name) is True

    def test_write_tools(self) -> None:
        for name in ("file_write", "file_edit", "shell", "git"):
            assert is_read_only_tool(name) is False

    def test_unknown_tool_is_write(self) -> None:
        assert is_read_only_tool("unknown_tool") is False

    def test_todo_write_is_write(self) -> None:
        assert is_read_only_tool("todo_write") is False

    def test_dispatch_agent_is_write(self) -> None:
        assert is_read_only_tool("dispatch_agent") is False


class TestBatcher:
    def test_empty_input(self) -> None:
        assert batch_tool_calls([]) == []

    def test_all_read_single_batch(self) -> None:
        calls = [
            {"function": {"name": "file_read"}},
            {"function": {"name": "search"}},
        ]
        batches = batch_tool_calls(calls)
        assert len(batches) == 1
        assert len(batches[0]) == 2

    def test_all_write_single_sequential_batch(self) -> None:
        calls = [
            {"function": {"name": "file_write"}},
            {"function": {"name": "file_edit"}},
        ]
        batches = batch_tool_calls(calls)
        assert len(batches) == 1
        assert len(batches[0]) == 2

    def test_mixed_tools_grouping(self) -> None:
        calls = [
            {"function": {"name": "file_read"}},
            {"function": {"name": "search"}},
            {"function": {"name": "file_write"}},
            {"function": {"name": "file_read"}},
            {"function": {"name": "glob_files"}},
            {"function": {"name": "shell"}},
        ]
        batches = batch_tool_calls(calls)
        assert len(batches) == 4
        assert len(batches[0]) == 2
        assert batches[0][0]["function"]["name"] == "file_read"
        assert batches[1][0]["function"]["name"] == "file_write"
        assert len(batches[2]) == 2
        assert batches[3][0]["function"]["name"] == "shell"


class TestExecutor:
    @pytest.mark.asyncio
    async def test_empty_tool_calls(self) -> None:
        result = await execute_parallel_batch([], None, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_sequential_execution_for_writes(self) -> None:
        call_order: list[str] = []

        class FakeToolNode:
            async def ainvoke(self, data):
                tc = data["messages"][-1]["tool_calls"][0]
                call_order.append(tc["function"]["name"])
                return {"messages": [{"tool_call_id": tc.get("id", "")}]}

        calls = [
            {"id": "1", "function": {"name": "file_write", "arguments": "{}"}},
            {"id": "2", "function": {"name": "file_edit", "arguments": "{}"}},
        ]
        await execute_parallel_batch(
            calls, FakeToolNode(), [{"role": "assistant", "tool_calls": calls}]
        )
        assert call_order == ["file_write", "file_edit"]
