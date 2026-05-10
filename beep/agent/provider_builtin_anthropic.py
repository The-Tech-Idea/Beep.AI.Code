"""Built-in Anthropic provider for autonomous-agent backends."""

from __future__ import annotations

from typing import Any

import httpx

from beep.agent.backends import ANTHROPIC_API_VERSION, AgentModelBackend, AnthropicMessagesAgentBackend
from beep.agent.provider_capabilities import ProviderCapabilities, ProviderDescriptor
from beep.agent.provider_contracts import AgentBackendProvider, ProviderProbeResult
from beep.config import BeepConfig
from beep.runtime.capabilities import CapabilityFlag


class AnthropicBackendProvider(AgentBackendProvider):
    """Built-in provider for Anthropic's hosted Messages API."""

    key = "anthropic"
    display_name = "Anthropic"
    _default_base_url = "https://api.anthropic.com"

    def requires_api_key(self) -> bool | None:
        return True

    def requires_model(self) -> bool | None:
        return True

    def default_base_url(self) -> str | None:
        return self._default_base_url

    def _resolve_base_url(self, config: BeepConfig) -> str:
        if config.agent_base_url and config.agent_base_url.strip():
            return config.agent_base_url.rstrip("/")
        return self._default_base_url

    def _resolve_api_key(self, config: BeepConfig) -> str | None:
        token = config.agent_api_key
        if token is None:
            return None
        return token.strip() or None

    def configuration_notes(self, config: BeepConfig) -> tuple[str, ...]:
        del config
        return (
            "Uses Anthropic's hosted Messages API by default.",
            "Set agent_model to a concrete Claude model such as claude-sonnet-4-20250514.",
            "Set agent_api_key to your Anthropic API key; agent_base_url is optional unless you are routing through a compatible gateway.",
        )

    def is_configured(self, config: BeepConfig) -> bool:
        return bool(self._resolve_base_url(config)) and self._resolve_api_key(config) is not None and config.effective_agent_model is not None

    def describe(self, config: BeepConfig) -> ProviderDescriptor:
        del config
        return ProviderDescriptor(
            key=self.key,
            display_name=self.display_name,
            capabilities=ProviderCapabilities(
                chat_completion=CapabilityFlag(
                    True,
                    "Uses Anthropic's hosted Messages API.",
                ),
                tool_calling=CapabilityFlag(
                    True,
                    "Tool payloads are translated into Anthropic tool definitions and tool_use blocks.",
                ),
                streaming=CapabilityFlag(
                    True,
                    "Streams Anthropic Messages API deltas through the autonomous agent runtime, including incremental text and tool-use assembly.",
                ),
                structured_output=CapabilityFlag(
                    False,
                    "OpenAI-style response_format is not part of the Anthropic Messages API adapter used by the autonomous agent backend.",
                ),
                vision=CapabilityFlag(
                    True,
                    "Normalizes OpenAI-style image_url content blocks into Anthropic image blocks when the vision input uses a base64 data URL.",
                ),
                embeddings=CapabilityFlag(
                    False,
                    "Embeddings are outside the autonomous agent backend contract.",
                ),
                local_model_runtime=CapabilityFlag(
                    False,
                    "Anthropic is a hosted provider, not an in-process local runtime.",
                ),
            ),
        )

    async def probe_configuration(self, config: BeepConfig) -> ProviderProbeResult:
        api_key = self._resolve_api_key(config)
        model = config.effective_agent_model
        if api_key is None or model is None:
            return ProviderProbeResult(
                supported=False,
                success=False,
                message="Anthropic validation requires both agent_api_key and agent_model.",
            )

        payload = {
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._resolve_base_url(config),
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                },
                timeout=httpx.Timeout(config.request_timeout, connect=10.0),
            ) as client:
                response = await client.post("/v1/messages", json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.text
            except Exception:
                detail = str(exc)
            return ProviderProbeResult(supported=True, success=False, message=detail or str(exc))
        except Exception as exc:
            return ProviderProbeResult(supported=True, success=False, message=str(exc))

        return ProviderProbeResult(
            supported=True,
            success=True,
            message=f"Connected to /v1/messages using Anthropic model '{model}'.",
        )

    def build_backend(
        self,
        config: BeepConfig,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> AgentModelBackend:
        del client
        del coding_assistant
        api_key = self._resolve_api_key(config)
        model = config.effective_agent_model
        if api_key is None or model is None:
            raise ValueError("Anthropic provider requires both an API key and a model.")
        return AnthropicMessagesAgentBackend(
            base_url=self._resolve_base_url(config),
            api_key=api_key,
            model=model,
            max_tokens=config.max_tokens,
            request_timeout=config.request_timeout,
        )