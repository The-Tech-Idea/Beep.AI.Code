"""Built-in OpenRouter provider for autonomous-agent backends."""

from __future__ import annotations

from typing import Any

from beep.agent.provider_base import OpenAICompatibleBackendProvider, _default_capabilities
from beep.config import BeepConfig


class OpenRouterBackendProvider(OpenAICompatibleBackendProvider):
    """Built-in provider for OpenRouter's hosted OpenAI-compatible API."""

    key = "openrouter"
    display_name = "OpenRouter"
    _default_base_url = "https://openrouter.ai/api"

    def _resolve_base_url(self, config: BeepConfig) -> str:
        if config.agent_base_url and config.agent_base_url.strip():
            return config.agent_base_url.rstrip("/")
        return self._default_base_url

    def _requires_model(self) -> bool:
        return True

    def default_base_url(self) -> str | None:
        return self._default_base_url

    def configuration_notes(self, config: BeepConfig) -> tuple[str, ...]:
        del config
        return (
            "Uses OpenRouter's hosted OpenAI-compatible API by default.",
            "Set agent_model to a concrete routed model such as anthropic/claude-sonnet-4 or openai/gpt-4.1-mini.",
            "Set agent_api_key to your OpenRouter API key; agent_base_url is optional unless you are routing through a custom compatible gateway.",
        )

    def _build_capabilities(self) -> Any:
        return _default_capabilities(
            chat_description="Uses OpenRouter's hosted OpenAI-compatible chat API.",
            tool_description="Tool payloads are forwarded through the OpenAI-compatible transport; actual support depends on the routed model.",
            structured_output=True,
            structured_output_description="Forwards response_format through OpenRouter's OpenAI-compatible chat API when the routed model supports structured outputs.",
            vision=True,
            vision_description="Preserves OpenAI-style multimodal message blocks such as image_url; actual vision support depends on the routed model.",
            local_runtime=False,
            local_runtime_description="OpenRouter is a hosted provider, not an in-process local runtime.",
        )