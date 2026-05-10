"""User-facing provider option shaping for autonomous-agent requests."""

from __future__ import annotations

from typing import Any

from beep.config import BeepConfig


_OPENAI_STYLE_BACKENDS = frozenset(
    {"openai", "openai-compatible", "openrouter", "lm-studio", "ollama"}
)
_REASONING_EFFORTS = frozenset({"low", "medium", "high"})


def normalize_reasoning_effort(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in _REASONING_EFFORTS:
        raise ValueError(
            f"agent_reasoning_effort must be one of: {', '.join(sorted(_REASONING_EFFORTS))}"
        )
    return normalized


def build_agent_provider_options(config: BeepConfig) -> dict[str, Any] | None:
    backend_key = str(config.agent_backend or "").strip().lower()
    options: dict[str, Any] = {}

    if backend_key in _OPENAI_STYLE_BACKENDS:
        reasoning_effort = normalize_reasoning_effort(config.agent_reasoning_effort)
        if reasoning_effort is not None:
            options["reasoning"] = {"effort": reasoning_effort}
        if config.agent_parallel_tool_calls is not None:
            options["parallel_tool_calls"] = config.agent_parallel_tool_calls

    if backend_key == "anthropic" and config.agent_thinking_budget_tokens is not None:
        options["thinking"] = {
            "type": "enabled",
            "budget_tokens": int(config.agent_thinking_budget_tokens),
        }

    return options or None


def describe_agent_provider_options(config: BeepConfig) -> list[tuple[str, str]]:
    backend_key = str(config.agent_backend or "").strip().lower()
    rows: list[tuple[str, str]] = []

    if backend_key in _OPENAI_STYLE_BACKENDS:
        reasoning_effort = normalize_reasoning_effort(config.agent_reasoning_effort)
        if reasoning_effort is not None:
            rows.append(("Reasoning Effort", reasoning_effort))
        if config.agent_parallel_tool_calls is not None:
            rows.append(
                (
                    "Parallel Tool Calls",
                    "Enabled" if config.agent_parallel_tool_calls else "Disabled",
                )
            )

    if backend_key == "anthropic" and config.agent_thinking_budget_tokens is not None:
        rows.append(("Thinking Budget", str(config.agent_thinking_budget_tokens)))

    return rows