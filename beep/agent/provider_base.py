"""Shared base classes for agent backend providers."""

from __future__ import annotations

from typing import Any

import httpx

from beep.agent.provider_capabilities import ProviderCapabilities
from beep.agent.provider_contracts import AgentBackendProvider, ProviderProbeResult
from beep.config import BeepConfig
from beep.runtime.capabilities import CapabilityFlag


def _default_capabilities(
    *,
    chat_description: str = "Uses a standard /v1/chat/completions endpoint.",
    tool_description: str = "Agent tools are sent through the standard tools payload.",
    streaming: bool = True,
    streaming_description: str = "Streams provider deltas through the autonomous agent runtime when the compatible endpoint supports SSE chat completions.",
    structured_output: bool = False,
    structured_output_description: str = "Compatible providers can forward response_format, but the autonomous agent runtime does not yet define a first-class structured-output workflow.",
    vision: bool = False,
    vision_description: str = "Vision or multimodal message shaping is not exposed by the current adapter.",
    embeddings: bool = False,
    embeddings_description: str = "Embeddings are outside the autonomous agent backend contract.",
    local_runtime: bool = False,
    local_runtime_description: str = "Generic OpenAI-compatible transport does not imply an in-process local runtime.",
) -> ProviderCapabilities:
    """Build a ProviderCapabilities with sensible defaults."""
    return ProviderCapabilities(
        chat_completion=CapabilityFlag(True, chat_description),
        tool_calling=CapabilityFlag(True, tool_description),
        streaming=CapabilityFlag(streaming, streaming_description),
        structured_output=CapabilityFlag(structured_output, structured_output_description),
        vision=CapabilityFlag(vision, vision_description),
        embeddings=CapabilityFlag(embeddings, embeddings_description),
        local_model_runtime=CapabilityFlag(local_runtime, local_runtime_description),
    )


class LocalOpenAICompatibleProvider(AgentBackendProvider):
    """Base for local OpenAI-compatible runtimes (LM Studio, Ollama, etc.).

    Subclasses only need to set:
        - key: provider identifier
        - display_name: human-readable name
        - _default_base_url: default URL for the local runtime
        - configuration_notes(): provider-specific setup instructions
        - _build_capabilities(): provider-specific capability flags
    """

    key: str = ""
    display_name: str = ""
    _default_base_url: str = ""

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

    def _requires_api_key(self) -> bool:
        return False

    def _requires_model(self) -> bool:
        return True

    def requires_api_key(self) -> bool | None:
        return self._requires_api_key()

    def requires_model(self) -> bool | None:
        return self._requires_model()

    def is_configured(self, config: BeepConfig) -> bool:
        has_base_url = bool(self._resolve_base_url(config))
        has_api_key = self._resolve_api_key(config) is not None
        has_model = config.effective_agent_model is not None
        if self._requires_api_key() and not has_api_key:
            return False
        if self._requires_model() and not has_model:
            return False
        return has_base_url

    def describe(self, config: BeepConfig) -> Any:
        from beep.agent.provider_capabilities import ProviderDescriptor

        return ProviderDescriptor(
            key=self.key,
            display_name=self.display_name,
            capabilities=self._build_capabilities(),
        )


class OpenAICompatibleBackendProvider(AgentBackendProvider):
    """Built-in provider for generic OpenAI-compatible transports."""

    key = "openai-compatible"
    display_name = "OpenAI-Compatible"

    def _resolve_base_url(self, config: BeepConfig) -> str:
        return config.effective_agent_base_url

    def _resolve_api_key(self, config: BeepConfig) -> str | None:
        return config.effective_agent_api_key

    def _requires_api_key(self) -> bool:
        return True

    def _requires_model(self) -> bool:
        return False

    def requires_api_key(self) -> bool | None:
        return self._requires_api_key()

    def requires_model(self) -> bool | None:
        return self._requires_model()

    def default_base_url(self) -> str | None:
        return None

    def configuration_notes(self, config: BeepConfig) -> tuple[str, ...]:
        del config
        return (
            "Requires an OpenAI-compatible base URL and API key.",
            "Use this for generic remote providers that expose /v1/chat/completions.",
        )

    async def probe_configuration(self, config: BeepConfig) -> ProviderProbeResult:
        from beep.agent.provider_probe_helpers import _build_model_probe_result

        headers: dict[str, str] = {}
        api_key = self._resolve_api_key(config)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            async with httpx.AsyncClient(
                base_url=self._resolve_base_url(config).rstrip("/") + "/",
                headers=headers,
                timeout=httpx.Timeout(config.request_timeout, connect=10.0),
            ) as client:
                response = await client.get("v1/models")
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.text
            except Exception:
                detail = str(exc)
            return ProviderProbeResult(supported=True, success=False, message=detail or str(exc))
        except Exception as exc:
            return ProviderProbeResult(supported=True, success=False, message=str(exc))

        models = data.get("data", []) if isinstance(data, dict) else []
        return _build_model_probe_result(models, selected_model=config.effective_agent_model)

    def _build_capabilities(self) -> ProviderCapabilities:
        return _default_capabilities(
            structured_output=True,
            structured_output_description=(
                "Forwards response_format through the OpenAI-compatible transport; actual support depends on the configured provider and model."
            ),
            vision=True,
            vision_description=(
                "Preserves OpenAI-style multimodal message content blocks such as image_url; actual vision support depends on the configured provider and model."
            ),
        )

    def is_configured(self, config: BeepConfig) -> bool:
        has_base_url = bool(self._resolve_base_url(config))
        has_api_key = self._resolve_api_key(config) is not None
        has_model = config.effective_agent_model is not None
        if self._requires_api_key() and not has_api_key:
            return False
        if self._requires_model() and not has_model:
            return False
        return has_base_url

    def describe(self, config: BeepConfig) -> Any:
        from beep.agent.provider_capabilities import ProviderDescriptor

        return ProviderDescriptor(
            key=self.key,
            display_name=self.display_name,
            capabilities=self._build_capabilities(),
        )

    def build_backend(
        self,
        config: BeepConfig,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> Any:
        from beep.agent.backends import OpenAICompatibleAgentBackend

        del client
        del coding_assistant
        return OpenAICompatibleAgentBackend(
            base_url=self._resolve_base_url(config),
            api_key=self._resolve_api_key(config),
            model=config.effective_agent_model,
            request_timeout=config.request_timeout,
        )
