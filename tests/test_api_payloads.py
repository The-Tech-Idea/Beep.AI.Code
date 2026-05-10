"""Tests for API payload builders."""

from __future__ import annotations

from beep.api.payloads import (
    build_anthropic_messages_payload,
    build_chat_completion_payload,
    build_openai_responses_payload,
)
from beep.config import BeepConfig


def test_build_chat_completion_payload_applies_defaults() -> None:
    config = BeepConfig(default_model="model-a", max_tokens=100, temperature=0.2)

    payload = build_chat_completion_payload(
        config,
        messages=[{"role": "user", "content": "hi"}],
    )

    assert payload["model"] == "model-a"
    assert payload["max_tokens"] == 100
    assert payload["temperature"] == 0.2


def test_build_chat_completion_payload_adds_stream_tools_and_coding_metadata() -> None:
    config = BeepConfig()

    payload = build_chat_completion_payload(
        config,
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
        tools=[{"type": "function"}],
        coding_assistant={"project_id": 1},
    )

    assert payload["stream"] is True
    assert payload["tools"] == [{"type": "function"}]
    assert payload["coding_assistant"] == {"project_id": 1}


# ---------------------------------------------------------------------------
# build_anthropic_messages_payload
# ---------------------------------------------------------------------------

def test_build_anthropic_messages_payload_minimal() -> None:
    config = BeepConfig(default_model="claude-sonnet")
    payload = build_anthropic_messages_payload(
        config,
        messages=[{"role": "user", "content": "hello"}],
    )
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert payload["model"] == "claude-sonnet"
    assert payload["max_tokens"] == 4096
    assert "system" not in payload
    assert "tools" not in payload
    assert "thinking" not in payload


def test_build_anthropic_messages_payload_with_all_optional_fields() -> None:
    config = BeepConfig()
    tools = [{"name": "bash", "description": "run shell", "input_schema": {"type": "object"}}]
    thinking = {"type": "enabled", "budget_tokens": 8000}
    payload = build_anthropic_messages_payload(
        config,
        messages=[{"role": "user", "content": "hi"}],
        model="claude-opus-4",
        max_tokens=2048,
        system="You are a coder.",
        tools=tools,
        thinking=thinking,
    )
    assert payload["model"] == "claude-opus-4"
    assert payload["max_tokens"] == 2048
    assert payload["system"] == "You are a coder."
    assert payload["tools"] == tools
    assert payload["thinking"] == thinking


# ---------------------------------------------------------------------------
# build_openai_responses_payload
# ---------------------------------------------------------------------------

def test_build_openai_responses_payload_string_input() -> None:
    config = BeepConfig(default_model="gpt-4o")
    payload = build_openai_responses_payload(config, input="say hello")
    assert payload["input"] == "say hello"
    assert payload["model"] == "gpt-4o"
    assert "previous_response_id" not in payload
    assert "reasoning" not in payload


def test_build_openai_responses_payload_list_input() -> None:
    config = BeepConfig()
    items = [{"type": "message", "role": "user", "content": "hi"}]
    payload = build_openai_responses_payload(config, input=items, model="gpt-4o-mini")
    assert payload["input"] == items
    assert payload["model"] == "gpt-4o-mini"


def test_build_openai_responses_payload_with_continuation_fields() -> None:
    config = BeepConfig()
    payload = build_openai_responses_payload(
        config,
        input="continue",
        model="gpt-4o",
        previous_response_id="resp_abc123",
        reasoning={"effort": "high"},
    )
    assert payload["previous_response_id"] == "resp_abc123"
    assert payload["reasoning"] == {"effort": "high"}
