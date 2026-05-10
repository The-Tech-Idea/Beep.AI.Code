from __future__ import annotations

from beep.agent.provider_options import build_agent_provider_options
from beep.config import BeepConfig


def test_build_agent_provider_options_for_openai_style_backends() -> None:
    config = BeepConfig(
        agent_backend="openrouter",
        agent_reasoning_effort="high",
        agent_parallel_tool_calls=False,
    )

    assert build_agent_provider_options(config) == {
        "reasoning": {"effort": "high"},
        "parallel_tool_calls": False,
    }


def test_build_agent_provider_options_for_anthropic() -> None:
    config = BeepConfig(
        agent_backend="anthropic",
        agent_thinking_budget_tokens=2048,
    )

    assert build_agent_provider_options(config) == {
        "thinking": {"type": "enabled", "budget_tokens": 2048}
    }


def test_build_agent_provider_options_does_not_forward_other_backends() -> None:
    config = BeepConfig(
        agent_backend="beep",
        agent_reasoning_effort="high",
        agent_parallel_tool_calls=True,
        agent_thinking_budget_tokens=4096,
    )

    assert build_agent_provider_options(config) is None