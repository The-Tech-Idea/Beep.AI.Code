"""Tests for typed agent provider-capability descriptors."""

from __future__ import annotations

from types import SimpleNamespace

from beep.agent.provider_capabilities import build_provider_descriptor
from beep.config import BeepConfig


def test_build_provider_descriptor_for_beep_backend() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(server_url="http://localhost:5000", api_token="token")
    )

    assert descriptor.key == "beep"
    assert descriptor.display_name == "Beep.AI.Server"
    assert descriptor.capabilities.chat_completion.exists is True
    assert descriptor.capabilities.tool_calling.exists is True
    assert descriptor.capabilities.streaming.exists is True
    assert descriptor.capabilities.structured_output.exists is True
    assert descriptor.capabilities.vision.exists is True


def test_build_provider_descriptor_for_openai_compatible_backend() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(
            agent_backend="openai-compatible",
            agent_base_url="http://provider.test",
            agent_api_key="provider-token",
            agent_model="model-x",
        )
    )

    assert descriptor.key == "openai-compatible"
    assert descriptor.display_name == "OpenAI-Compatible"
    assert descriptor.capabilities.chat_completion.exists is True
    assert descriptor.capabilities.tool_calling.exists is True
    assert descriptor.capabilities.structured_output.exists is True
    assert descriptor.capabilities.vision.exists is True
    assert descriptor.capabilities.local_model_runtime.exists is False


def test_build_provider_descriptor_for_openai_backend() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(
            agent_backend="openai",
            agent_api_key="openai-token",
            agent_model="gpt-4.1-mini",
        )
    )

    assert descriptor.key == "openai"
    assert descriptor.display_name == "OpenAI"
    assert descriptor.capabilities.chat_completion.exists is True
    assert descriptor.capabilities.tool_calling.exists is True
    assert descriptor.capabilities.structured_output.exists is True
    assert descriptor.capabilities.vision.exists is True
    assert descriptor.capabilities.local_model_runtime.exists is False


def test_build_provider_descriptor_for_anthropic_backend() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(
            agent_backend="anthropic",
            agent_api_key="anthropic-token",
            agent_model="claude-sonnet-4-20250514",
        )
    )

    assert descriptor.key == "anthropic"
    assert descriptor.display_name == "Anthropic"
    assert descriptor.capabilities.chat_completion.exists is True
    assert descriptor.capabilities.tool_calling.exists is True
    assert descriptor.capabilities.streaming.exists is True
    assert descriptor.capabilities.structured_output.exists is False
    assert descriptor.capabilities.vision.exists is True
    assert descriptor.capabilities.local_model_runtime.exists is False


def test_build_provider_descriptor_for_openrouter_backend() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(
            agent_backend="openrouter",
            agent_api_key="openrouter-token",
            agent_model="anthropic/claude-sonnet-4",
        )
    )

    assert descriptor.key == "openrouter"
    assert descriptor.display_name == "OpenRouter"
    assert descriptor.capabilities.chat_completion.exists is True
    assert descriptor.capabilities.tool_calling.exists is True
    assert descriptor.capabilities.structured_output.exists is True
    assert descriptor.capabilities.vision.exists is True
    assert descriptor.capabilities.local_model_runtime.exists is False


def test_build_provider_descriptor_for_lm_studio_backend() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(agent_backend="lm-studio", agent_model="qwen-coder")
    )

    assert descriptor.key == "lm-studio"
    assert descriptor.display_name == "LM Studio"
    assert descriptor.capabilities.chat_completion.exists is True
    assert descriptor.capabilities.tool_calling.exists is True
    assert descriptor.capabilities.structured_output.exists is True
    assert descriptor.capabilities.vision.exists is True
    assert descriptor.capabilities.local_model_runtime.exists is True


def test_build_provider_descriptor_for_ollama_backend() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(agent_backend="ollama", agent_model="qwen2.5-coder")
    )

    assert descriptor.key == "ollama"
    assert descriptor.display_name == "Ollama"
    assert descriptor.capabilities.chat_completion.exists is True
    assert descriptor.capabilities.tool_calling.exists is True
    assert descriptor.capabilities.structured_output.exists is True
    assert descriptor.capabilities.vision.exists is True
    assert descriptor.capabilities.local_model_runtime.exists is True


def test_build_provider_descriptor_uses_runtime_plugin_provider() -> None:
    descriptor = build_provider_descriptor(
        BeepConfig(agent_backend="custom-provider"),
        plugin_registry=SimpleNamespace(
            get_backend_provider=lambda key: SimpleNamespace(
                describe=lambda config: SimpleNamespace(key=key, display_name="Custom Provider", capabilities=SimpleNamespace())
            ) if key == "custom-provider" else None
        ),
    )

    assert descriptor.key == "custom-provider"
    assert descriptor.display_name == "Custom Provider"