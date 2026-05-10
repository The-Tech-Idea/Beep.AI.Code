"""Tests for agent message normalization and LangChain message conversion."""

from __future__ import annotations

import json
from unittest.mock import patch

from beep.agent.message_adapter import (
    agent_dict_to_langchain_message,
    agent_messages_to_langchain_messages,
    extract_agent_completion,
    langchain_message_to_agent_dict,
    langchain_messages_to_agent_dicts,
    tool_result_to_langchain_message,
)


class _FakeBaseMessage:
    def __init__(self, *, content: str = "", **kwargs) -> None:
        self.content = content
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeSystemMessage(_FakeBaseMessage):
    pass


class _FakeHumanMessage(_FakeBaseMessage):
    pass


class _FakeAIMessage(_FakeBaseMessage):
    def __init__(
        self, *, content: str = "", tool_calls: list[dict] | None = None, **kwargs
    ) -> None:
        super().__init__(content=content, tool_calls=tool_calls or [], **kwargs)


class _FakeToolMessage(_FakeBaseMessage):
    def __init__(self, *, content: str = "", tool_call_id: str = "", **kwargs) -> None:
        super().__init__(content=content, tool_call_id=tool_call_id, **kwargs)


def _fake_message_types() -> tuple[type, type, type, type]:
    return _FakeSystemMessage, _FakeHumanMessage, _FakeAIMessage, _FakeToolMessage


def test_extract_agent_completion_normalizes_tool_calls() -> None:
    completion = extract_agent_completion(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "file_read",
                                    "arguments": {"file_path": "x.txt"},
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        }
    )
    assert completion.tool_calls[0]["function"]["name"] == "file_read"
    assert completion.tool_calls[0]["function"]["arguments"] == json.dumps({"file_path": "x.txt"})
    assert completion.usage == {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}


def test_assistant_message_round_trips_with_tool_calls() -> None:
    message = {
        "role": "assistant",
        "content": "I will inspect the file.",
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "file_read",
                    "arguments": {"file_path": "x.txt"},
                },
            }
        ],
    }
    with patch(
        "beep.agent.message_adapter._load_langchain_message_types",
        return_value=_fake_message_types(),
    ):
        langchain_message = agent_dict_to_langchain_message(message)
        round_tripped = langchain_message_to_agent_dict(langchain_message)

    assert isinstance(langchain_message, _FakeAIMessage)
    assert langchain_message.tool_calls[0]["name"] == "file_read"
    assert langchain_message.tool_calls[0]["args"] == {"file_path": "x.txt"}
    assert round_tripped == {
        "role": "assistant",
        "content": "I will inspect the file.",
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "file_read",
                    "arguments": json.dumps({"file_path": "x.txt"}),
                },
            }
        ],
    }


def test_message_list_helpers_round_trip_system_user_and_tool_messages() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "tool", "tool_call_id": "call-2", "content": "done"},
    ]
    with patch(
        "beep.agent.message_adapter._load_langchain_message_types",
        return_value=_fake_message_types(),
    ):
        lc_messages = agent_messages_to_langchain_messages(messages)
        round_tripped = langchain_messages_to_agent_dicts(lc_messages)

    assert [type(message) for message in lc_messages] == [
        _FakeSystemMessage,
        _FakeHumanMessage,
        _FakeToolMessage,
    ]
    assert round_tripped == messages


def test_user_multimodal_message_round_trips_without_stringifying() -> None:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "inspect this"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}},
            ],
        }
    ]
    with patch(
        "beep.agent.message_adapter._load_langchain_message_types",
        return_value=_fake_message_types(),
    ):
        lc_messages = agent_messages_to_langchain_messages(messages)
        round_tripped = langchain_messages_to_agent_dicts(lc_messages)

    assert lc_messages[0].content == messages[0]["content"]
    assert round_tripped == messages


def test_tool_result_to_langchain_message_uses_tool_call_id() -> None:
    with patch(
        "beep.agent.message_adapter._load_langchain_message_types",
        return_value=_fake_message_types(),
    ):
        message = tool_result_to_langchain_message(tool_call_id="call-3", content="patched")
    assert isinstance(message, _FakeToolMessage)
    assert message.tool_call_id == "call-3"
    assert message.content == "patched"
