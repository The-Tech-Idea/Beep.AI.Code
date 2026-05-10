"""Tests for BaseTool -> LangChain tool adaptation."""

from __future__ import annotations

import json

import pytest

from beep.agent.tool_adapter import (
    adapt_tool,
    adapt_tools,
    build_tool_args_schema,
    execute_adapted_tool,
    parse_tool_exception,
)
from beep.agent.tools.base import BaseTool, ToolResult


class _DummyTool(BaseTool):
    def __init__(self, result: ToolResult) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    @property
    def name(self) -> str:
        return "dummy_tool"

    @property
    def description(self) -> str:
        return "Dummy tool for adapter tests"

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "path": {"type": "string", "description": "Path to inspect"},
            "line": {"type": "integer", "description": "Line number"},
            "allow_missing": {"type": "boolean", "description": "Allow missing values"},
        }

    @property
    def optional_params(self) -> list[str]:
        return ["line", "allow_missing"]

    async def execute(self, **kwargs):
        self.calls.append(dict(kwargs))
        return self._result


class _FakeToolException(Exception):
    pass


class _FakeStructuredTool:
    def __init__(self, *, coroutine, name, description, args_schema) -> None:
        self.coroutine = coroutine
        self.name = name
        self.description = description
        self.args_schema = args_schema

    @classmethod
    def from_function(cls, *, coroutine, name, description, args_schema):
        return cls(
            coroutine=coroutine,
            name=name,
            description=description,
            args_schema=args_schema,
        )

    async def ainvoke(self, payload: dict[str, object]) -> str:
        return await self.coroutine(**payload)


def test_build_tool_args_schema_marks_optional_fields() -> None:
    args_schema = build_tool_args_schema(_DummyTool(ToolResult(success=True, output="ok")))
    schema = args_schema.model_json_schema()
    assert schema["required"] == ["path"]
    assert schema["properties"]["path"]["type"] == "string"
    assert {entry["type"] for entry in schema["properties"]["line"]["anyOf"]} == {"integer", "null"}
    assert {entry["type"] for entry in schema["properties"]["allow_missing"]["anyOf"]} == {"boolean", "null"}


@pytest.mark.asyncio
async def test_adapt_tool_returns_structured_tool_and_truncates_success_output(monkeypatch) -> None:
    tool = _DummyTool(ToolResult(success=True, output="abcdefghijklmnopqrstuvwxyz"))
    monkeypatch.setattr(
        "beep.agent.tool_adapter._load_langchain_tool_primitives",
        lambda: (_FakeStructuredTool, _FakeToolException),
    )
    monkeypatch.setattr("beep.agent.tool_adapter.requires_approval", lambda name, kwargs: False)

    adapted = adapt_tool(tool, max_output_chars=10)
    output = await adapted.ainvoke({"path": "file.txt", "line": 3})

    assert adapted.name == "dummy_tool"
    assert "truncated at 10 chars" in output
    assert tool.calls == [{"path": "file.txt", "line": 3}]


@pytest.mark.asyncio
async def test_adapt_tool_preserves_approval_checks(monkeypatch) -> None:
    tool = _DummyTool(ToolResult(success=True, output="ok"))
    monkeypatch.setattr(
        "beep.agent.tool_adapter._load_langchain_tool_primitives",
        lambda: (_FakeStructuredTool, _FakeToolException),
    )
    monkeypatch.setattr("beep.agent.tool_adapter.requires_approval", lambda name, kwargs: True)
    monkeypatch.setattr("beep.agent.tool_adapter.request_approval", lambda name, kwargs: False)

    adapted = adapt_tool(tool)
    with pytest.raises(_FakeToolException, match="User denied approval"):
        await adapted.ainvoke({"path": "file.txt"})
    assert tool.calls == []


@pytest.mark.asyncio
async def test_adapt_tool_can_disable_embedded_approval_checks(monkeypatch) -> None:
    tool = _DummyTool(ToolResult(success=True, output="ok"))
    monkeypatch.setattr(
        "beep.agent.tool_adapter._load_langchain_tool_primitives",
        lambda: (_FakeStructuredTool, _FakeToolException),
    )
    monkeypatch.setattr("beep.agent.tool_adapter.requires_approval", lambda name, kwargs: True)
    monkeypatch.setattr("beep.agent.tool_adapter.request_approval", lambda name, kwargs: False)

    adapted = adapt_tool(tool, require_human_approval=False)
    output = await adapted.ainvoke({"path": "file.txt"})

    assert output == "ok"
    assert tool.calls == [{"path": "file.txt"}]


@pytest.mark.asyncio
async def test_adapt_tool_raises_structured_error_payload_on_failure(monkeypatch) -> None:
    tool = _DummyTool(ToolResult(success=False, output="partial output", error="boom", is_error=True))
    monkeypatch.setattr(
        "beep.agent.tool_adapter._load_langchain_tool_primitives",
        lambda: (_FakeStructuredTool, _FakeToolException),
    )
    monkeypatch.setattr("beep.agent.tool_adapter.requires_approval", lambda name, kwargs: False)

    adapted = adapt_tool(tool)
    with pytest.raises(_FakeToolException) as exc_info:
        await adapted.ainvoke({"path": "file.txt"})

    payload = json.loads(str(exc_info.value))
    assert payload == {
        "tool_name": "dummy_tool",
        "error": "boom",
        "output": "partial output",
        "is_error": True,
    }


def test_adapt_tools_adapts_tool_list(monkeypatch) -> None:
    monkeypatch.setattr(
        "beep.agent.tool_adapter._load_langchain_tool_primitives",
        lambda: (_FakeStructuredTool, _FakeToolException),
    )
    monkeypatch.setattr("beep.agent.tool_adapter.requires_approval", lambda name, kwargs: False)
    adapted = adapt_tools(
        [
            _DummyTool(ToolResult(success=True, output="ok")),
            _DummyTool(ToolResult(success=True, output="ok2")),
        ]
    )
    assert len(adapted) == 2
    assert all(isinstance(tool, _FakeStructuredTool) for tool in adapted)


@pytest.mark.asyncio
async def test_execute_adapted_tool_coerces_success_output_dict() -> None:
    adapted = _FakeStructuredTool(
        coroutine=lambda **kwargs: None,
        name="dummy_tool",
        description="dummy",
        args_schema=None,
    )

    async def _return_dict(**kwargs):
        return {"path": kwargs["path"]}

    adapted.coroutine = _return_dict
    result = await execute_adapted_tool(adapted, tool_name="dummy_tool", arguments={"path": "file.txt"})
    assert result.success is True
    assert json.loads(result.output) == {"path": "file.txt"}


def test_parse_tool_exception_reads_structured_payload() -> None:
    result = parse_tool_exception(
        "dummy_tool",
        _FakeToolException(
            json.dumps(
                {
                    "tool_name": "dummy_tool",
                    "error": "boom",
                    "output": "partial",
                    "is_error": True,
                }
            )
        ),
    )
    assert result == ToolResult(success=False, output="partial", error="boom", is_error=True)