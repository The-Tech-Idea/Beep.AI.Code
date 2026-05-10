"""Shared test fixtures and mock server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from beep.api.client import BeepAPIClient
from beep.config import BeepConfig
from beep.runtime.workspace import clear_workspace_runtime_cache


@pytest.fixture(autouse=True)
def clear_runtime_cache_between_tests():
    """Keep cached workspace runtime state isolated between tests."""
    clear_workspace_runtime_cache()
    yield
    clear_workspace_runtime_cache()


@pytest.fixture
def mock_config(tmp_path: Path) -> BeepConfig:
    """Create a mock config."""
    return BeepConfig(
        server_url="http://localhost:8000",
        api_token="test-token-12345",
        default_model="gpt-4",
        max_tokens=4096,
        temperature=0.7,
    )


@pytest.fixture
def mock_client(mock_config: BeepConfig) -> BeepAPIClient:
    """Create a mock API client."""
    return BeepAPIClient(mock_config)


@pytest.fixture
def mock_workspace(tmp_path: Path) -> Path:
    """Create a mock workspace with sample files."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "def main():\n    print('hello')\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "utils.py").write_text(
        "def helper():\n    return 42\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Test Project\n",
        encoding="utf-8",
    )
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def sample_session_id() -> str:
    """Return a sample session ID."""
    return "test-session-001"


def mock_chat_response(
    content: str = "Hello!",
    tool_calls: list[dict[str, Any]] | None = None,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Create a mock chat completion response."""
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls

    return {
        "choices": [{"message": message, "finish_reason": "stop"}],
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def mock_tool_call(
    name: str,
    arguments: dict[str, Any],
    call_id: str = "call-1",
) -> dict[str, Any]:
    """Create a mock tool call."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }
