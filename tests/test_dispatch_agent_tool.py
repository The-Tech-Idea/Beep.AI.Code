"""Tests for the DispatchAgentTool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from beep.agent.subagents.dispatcher import SubAgentDispatcher
from beep.agent.tools.dispatch_agent import DispatchAgentTool


def _make_dispatcher(*, max_depth: int = 1, current_depth: int = 0) -> SubAgentDispatcher:
    return SubAgentDispatcher(
        workspace_root=Path.cwd(),
        all_tools=[],
        max_subagent_steps=10,
        current_depth=current_depth,
        max_depth=max_depth,
    )


@pytest.mark.asyncio
async def test_dispatch_agent_requires_task() -> None:
    tool = DispatchAgentTool(dispatcher=_make_dispatcher())
    result = await tool.execute(subagent_type="explore")
    assert result.success is False
    assert "task is required" in result.error


@pytest.mark.asyncio
async def test_dispatch_agent_rejects_unknown_type() -> None:
    tool = DispatchAgentTool(dispatcher=_make_dispatcher())
    result = await tool.execute(task="do something", subagent_type="invalid")
    assert result.success is False
    assert "Unknown sub-agent type" in result.error


@pytest.mark.asyncio
async def test_dispatch_agent_respects_depth_limit() -> None:
    tool = DispatchAgentTool(dispatcher=_make_dispatcher(max_depth=1, current_depth=1))
    result = await tool.execute(task="explore codebase", subagent_type="explore")
    assert result.success is False
    assert "maximum nesting depth reached" in result.error


@pytest.mark.asyncio
async def test_dispatch_agent_returns_success() -> None:
    tool = DispatchAgentTool(
        dispatcher=_make_dispatcher(),
        backend=MagicMock(),
        system_prompt="test prompt",
        session_id="test-session",
    )
    result = await tool.execute(task="find all API endpoints", subagent_type="explore")
    assert result.success is True
    assert "EXPLORE SUB-AGENT" in result.output
    assert "find all API endpoints" in result.output
