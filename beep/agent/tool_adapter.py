"""LangChain/LangGraph tool adaptation helpers for the autonomous agent runtime."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from beep.agent.approval import request_approval, requires_approval
from beep.agent.tools.base import BaseTool, ToolResult

DEFAULT_MAX_TOOL_OUTPUT_CHARS = 8_000


def _load_langchain_tool_primitives() -> tuple[Any, Any]:
    """Import LangChain Core tool primitives lazily for the managed agent environment."""
    try:
        from langchain_core.tools import StructuredTool, ToolException
    except ImportError as exc:
        raise RuntimeError(
            'LangChain Core tool primitives are not installed. Run "beep agent setup" to provision the managed agent environment.'
        ) from exc
    return StructuredTool, ToolException


def _annotation_for_parameter(schema: dict[str, Any]) -> Any:
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return Literal.__getitem__(tuple(enum_values))

    schema_type = str(schema.get("type", "string")).lower()
    if schema_type == "string":
        return str
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "object":
        return dict[str, Any]
    if schema_type == "array":
        items = schema.get("items")
        item_schema = items if isinstance(items, dict) else {"type": "string"}
        return list[_annotation_for_parameter(item_schema)]
    return Any


def build_tool_args_schema(tool: BaseTool) -> type[BaseModel]:
    """Build a Pydantic args_schema from a BaseTool JSON-schema-like parameter map."""
    field_definitions: dict[str, tuple[Any, Field]] = {}
    optional_params = set(tool.optional_params)
    for name, raw_schema in tool.parameters.items():
        schema = raw_schema if isinstance(raw_schema, dict) else {}
        annotation = _annotation_for_parameter(schema)
        is_optional = name in optional_params
        if is_optional:
            annotation = annotation | None
        default = None if is_optional else ...
        field_definitions[name] = (
            annotation,
            Field(default=default, description=str(schema.get("description", ""))),
        )

    model_name = f"{tool.__class__.__name__}Args"
    return create_model(model_name, **field_definitions)


def _truncate_output(output: str, max_output_chars: int) -> str:
    if len(output) <= max_output_chars:
        return output
    return output[:max_output_chars] + f"\n[... output truncated at {max_output_chars} chars]"


def _structured_error_payload(
    *,
    tool_name: str,
    error: str,
    output: str = "",
    is_error: bool = True,
) -> str:
    return json.dumps(
        {
            "tool_name": tool_name,
            "error": error,
            "output": output,
            "is_error": is_error,
        },
        ensure_ascii=False,
    )


def _coerce_text_output(value: Any) -> str:
    if value is None:
        return "(no output)"
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def parse_tool_exception(tool_name: str, exc: Exception) -> ToolResult:
    """Convert a structured tool exception back into the local ToolResult shape."""
    raw_error = str(exc)
    try:
        payload = json.loads(raw_error)
    except (TypeError, json.JSONDecodeError):
        return ToolResult(success=False, output="", error=raw_error or f"{tool_name} failed", is_error=True)

    if not isinstance(payload, dict):
        return ToolResult(success=False, output="", error=raw_error or f"{tool_name} failed", is_error=True)

    error = payload.get("error")
    output = payload.get("output")
    return ToolResult(
        success=False,
        output=_coerce_text_output(output) if output not in (None, "") else "",
        error=str(error) if error not in (None, "") else (raw_error or f"{tool_name} failed"),
        is_error=bool(payload.get("is_error", True)),
    )


async def execute_adapted_tool(adapted_tool: Any, *, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
    """Execute an adapted tool and coerce its result back into ToolResult."""
    try:
        output = await adapted_tool.ainvoke(arguments)
    except Exception as exc:
        return parse_tool_exception(tool_name, exc)
    return ToolResult(success=True, output=_coerce_text_output(output))


def adapt_tool(
    tool: BaseTool,
    *,
    max_output_chars: int = DEFAULT_MAX_TOOL_OUTPUT_CHARS,
    require_human_approval: bool = True,
) -> Any:
    """Adapt a BaseTool into a LangChain StructuredTool."""
    structured_tool_cls, tool_exception_cls = _load_langchain_tool_primitives()
    args_schema = build_tool_args_schema(tool)

    async def _run_tool(**kwargs: Any) -> str:
        if require_human_approval and requires_approval(tool.name, kwargs):
            if not request_approval(tool.name, kwargs):
                raise tool_exception_cls(
                    _structured_error_payload(
                        tool_name=tool.name,
                        error="User denied approval",
                    )
                )

        result = await tool.execute(**kwargs)
        output = _truncate_output(result.output or "", max_output_chars)
        if result.success:
            return output or "(no output)"

        raise tool_exception_cls(
            _structured_error_payload(
                tool_name=tool.name,
                error=result.error or f"{tool.name} failed",
                output=output,
                is_error=result.is_error or True,
            )
        )

    return structured_tool_cls.from_function(
        coroutine=_run_tool,
        name=tool.name,
        description=tool.description,
        args_schema=args_schema,
    )


def adapt_tools(
    tools: list[BaseTool],
    *,
    max_output_chars: int = DEFAULT_MAX_TOOL_OUTPUT_CHARS,
    require_human_approval: bool = True,
) -> list[Any]:
    """Adapt a list of BaseTool instances into LangChain StructuredTool objects."""
    return [
        adapt_tool(
            tool,
            max_output_chars=max_output_chars,
            require_human_approval=require_human_approval,
        )
        for tool in tools
    ]