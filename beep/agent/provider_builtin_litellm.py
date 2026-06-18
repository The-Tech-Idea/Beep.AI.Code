"""Built-in provider for LiteLLM's OpenAI-compatible gateway."""

from __future__ import annotations

from typing import Any

from beep.agent.provider_base import (
    OpenAICompatibleBackendProvider,
    _default_capabilities,
)
from beep.config import BeepConfig


class LiteLLMBackendProvider(OpenAICompatibleBackendProvider):
    """Built-in provider for LiteLLM's OpenAI-compatible gateway."""

    key = "litellm"
    display_name = "LiteLLM"
    _default_base_url = "http://localhost:4000"

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
            "LiteLLM is an OpenAI-compatible proxy/gateway.",
            "Set agent_base_url to your LiteLLM instance.",
            "Set agent_model to any model name your LiteLLM routes.",
            "Set agent_api_key to your LiteLLM virtual key, if required.",
        )

    def _build_capabilities(self) -> Any:
        return _default_capabilities(
            chat_description="Proxies requests through LiteLLM's OpenAI-compatible gateway.",
            tool_description=(
                "Tool payloads are forwarded through the OpenAI-compatible transport; "
                "actual tool support depends on the target model."
            ),
            structured_output=True,
            structured_output_description=(
                "Forwards response_format through LiteLLM's gateway when "
                "the target model supports structured outputs."
            ),
            vision=True,
            vision_description=(
                "Preserves multimodal message blocks such as image_url; "
                "actual vision support depends on the target model."
            ),
            local_runtime=False,
            local_runtime_description=(
                "LiteLLM is typically a hosted or self-hosted gateway, "
                "not an in-process local runtime."
            ),
        )
