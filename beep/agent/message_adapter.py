"""Message normalization and conversion helpers for the autonomous agent runtime."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class AgentCompletion:
    """Normalized completion payload returned by autonomous agent backends."""

    content: str | None
    tool_calls: list[dict[str, Any]]
    usage: dict[str, int] | None = None
    raw_response: dict[str, Any] | None = None


def _load_langchain_message_types() -> tuple[Any, Any, Any, Any]:
    """Import LangChain Core message types lazily for the managed agent environment."""
    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    except ImportError as exc:
        raise RuntimeError(
            'LangChain Core message primitives are not installed. Run "beep agent setup" to provision the managed agent environment.'
        ) from exc
    return SystemMessage, HumanMessage, AIMessage, ToolMessage


def _coerce_content(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        normalized: list[Any] = []
        for item in value:
            if isinstance(item, (str, dict, list)):
                normalized.append(item)
            else:
                normalized.append(str(item))
        return normalized
    return str(value)


def normalize_usage(usage: dict[str, Any] | None) -> dict[str, int] | None:
    """Normalize provider usage payloads into a consistent token-count shape."""
    if not isinstance(usage, dict):
        return None
    total_tokens = int(usage.get("total_tokens", 0) or 0)
    if total_tokens <= 0:
        return None
    return {
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": total_tokens,
    }


def normalize_tool_call(tool_call: dict[str, Any]) -> dict[str, Any]:
    """Normalize a provider tool-call payload into the agent's internal shape."""
    function = tool_call.get("function", {})
    arguments = function.get("arguments", "{}")
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments)
    return {
        "id": str(tool_call.get("id", "")),
        "type": str(tool_call.get("type", "function")),
        "function": {
            "name": str(function.get("name", "")),
            "arguments": arguments,
        },
    }


def extract_agent_completion(response: dict[str, Any]) -> AgentCompletion:
    """Normalize a chat completion response into the agent completion shape."""
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    raw_tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
    tool_calls: list[dict[str, Any]] = []
    if isinstance(raw_tool_calls, list):
        tool_calls = [
            normalize_tool_call(tool_call)
            for tool_call in raw_tool_calls
            if isinstance(tool_call, dict)
        ]
    return AgentCompletion(
        content=_coerce_content(content) if content is not None else None,
        tool_calls=tool_calls,
        usage=normalize_usage(response.get("usage")),
        raw_response=response,
    )


def agent_dict_to_langchain_message(message: dict[str, Any]) -> Any:
    """Convert an internal agent message dict into a LangChain Core message object."""
    system_cls, human_cls, ai_cls, tool_cls = _load_langchain_message_types()
    role = str(message.get("role", "")).strip().lower()
    content = _coerce_content(message.get("content"))

    if role == "system":
        return system_cls(content=content)
    if role == "user":
        return human_cls(content=content)
    if role == "assistant":
        raw_tool_calls = message.get("tool_calls") or []
        lc_tool_calls = []
        for tc in raw_tool_calls:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function", {})
            args_str = fn.get("arguments", "{}")
            if isinstance(args_str, str):
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
            elif isinstance(args_str, dict):
                args = args_str
            else:
                args = {}
            lc_tool_calls.append(
                {
                    "id": str(tc.get("id", "")),
                    "name": str(fn.get("name", "")),
                    "args": args,
                }
            )
        if lc_tool_calls:
            return ai_cls(content=content, tool_calls=lc_tool_calls)
        return ai_cls(content=content)
    if role == "tool":
        return tool_cls(content=content, tool_call_id=str(message.get("tool_call_id", "")))
    raise ValueError(f"Unsupported agent message role: {role or '<missing>'}")


def langchain_message_to_agent_dict(message: Any) -> dict[str, Any]:
    """Convert a LangChain Core message object into the internal agent dict shape."""
    system_cls, human_cls, ai_cls, tool_cls = _load_langchain_message_types()

    if isinstance(message, system_cls):
        return {"role": "system", "content": _coerce_content(getattr(message, "content", ""))}
    if isinstance(message, human_cls):
        return {"role": "user", "content": _coerce_content(getattr(message, "content", ""))}
    if isinstance(message, ai_cls):
        payload: dict[str, Any] = {
            "role": "assistant",
            "content": _coerce_content(getattr(message, "content", "")),
        }
        raw_tool_calls = getattr(message, "tool_calls", None)
        if isinstance(raw_tool_calls, list) and raw_tool_calls:
            normalized = []
            for tc in raw_tool_calls:
                if isinstance(tc, dict):
                    tc_id = tc.get("id", "")
                    tc_name = tc.get("name", "")
                    tc_args = tc.get("args", {})
                else:
                    tc_id = str(getattr(tc, "id", ""))
                    tc_name = str(getattr(tc, "name", ""))
                    tc_args = getattr(tc, "args", {})
                normalized.append(
                    {
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": tc_name,
                            "arguments": json.dumps(tc_args)
                            if isinstance(tc_args, dict)
                            else str(tc_args),
                        },
                    }
                )
            payload["tool_calls"] = normalized
        return payload
    if isinstance(message, tool_cls):
        return {
            "role": "tool",
            "tool_call_id": str(getattr(message, "tool_call_id", "")),
            "content": _coerce_content(getattr(message, "content", "")),
        }
    raise ValueError(f"Unsupported LangChain message type: {type(message)!r}")


def agent_messages_to_langchain_messages(messages: list[dict[str, Any]]) -> list[Any]:
    """Convert a list of internal agent messages into LangChain Core messages."""
    return [agent_dict_to_langchain_message(message) for message in messages]


def langchain_messages_to_agent_dicts(messages: list[Any]) -> list[dict[str, Any]]:
    """Convert a list of LangChain Core messages into internal agent message dicts."""
    return [langchain_message_to_agent_dict(message) for message in messages]


def tool_result_to_langchain_message(*, tool_call_id: str, content: str) -> Any:
    """Create a LangChain Core ToolMessage from an executed tool result."""
    _system_cls, _human_cls, _ai_cls, tool_cls = _load_langchain_message_types()
    return tool_cls(content=content, tool_call_id=tool_call_id)
