"""Built-in OpenAI-compatible providers for autonomous-agent backends."""

from __future__ import annotations

from typing import Any

import httpx

from beep.agent.backends import AgentModelBackend, OpenAICompatibleAgentBackend
from beep.agent.provider_base import (
    LocalOpenAICompatibleProvider,
    OpenAICompatibleBackendProvider,
    _default_capabilities,
)
from beep.agent.provider_contracts import ProviderProbeResult
from beep.agent.provider_probe_helpers import _build_model_probe_result
from beep.config import BeepConfig


# Re-export for backward compatibility
from beep.agent.provider_base import OpenAICompatibleBackendProvider  # noqa: F811


class OpenAIBackendProvider(OpenAICompatibleBackendProvider):
    """Built-in provider for OpenAI's hosted API."""

    key = "openai"
    display_name = "OpenAI"
    _default_base_url = "https://api.openai.com"

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
            "Uses OpenAI's hosted API by default.",
            "Set agent_model to a concrete OpenAI model such as gpt-4.1 or gpt-4.1-mini.",
            "Set agent_api_key to your OpenAI API key; agent_base_url is optional unless you are routing through a compatible gateway.",
        )

    def _build_capabilities(self) -> Any:
        return _default_capabilities(
            chat_description="Uses OpenAI's hosted /v1/chat/completions API by default.",
            tool_description="Tool payloads are forwarded through the OpenAI-compatible transport; actual support depends on the selected OpenAI model.",
            structured_output=True,
            structured_output_description="Forwards response_format through OpenAI's hosted chat API when the selected model supports structured outputs.",
            vision=True,
            vision_description="Preserves OpenAI multimodal message blocks, including image_url inputs, for models that support vision.",
            local_runtime=False,
            local_runtime_description="OpenAI is a hosted provider, not an in-process local runtime.",
        )


class LMStudioBackendProvider(LocalOpenAICompatibleProvider):
    """Built-in provider for LM Studio's local OpenAI-compatible runtime."""

    key = "lm-studio"
    display_name = "LM Studio"
    _default_base_url = "http://localhost:1234"

    def configuration_notes(self, config: BeepConfig) -> tuple[str, ...]:
        del config
        return (
            "Uses LM Studio's local OpenAI-compatible server by default.",
            "Set agent_model to a loaded local model such as qwen-coder or deepseek-coder.",
            "agent_api_key is optional for the default local LM Studio runtime.",
        )

    def _build_capabilities(self) -> Any:
        return _default_capabilities(
            chat_description="Wraps LM Studio's local OpenAI-compatible chat endpoint.",
            tool_description="Tool payloads are forwarded through the OpenAI-compatible transport; actual support depends on the loaded model.",
            structured_output=True,
            structured_output_description="Forwards response_format through LM Studio's OpenAI-compatible transport when the loaded model/runtime supports it.",
            vision=True,
            vision_description="Preserves OpenAI-style multimodal message blocks such as image_url; actual vision support depends on the loaded model/runtime.",
            local_runtime=True,
            local_runtime_description="Targets LM Studio's local desktop model runtime by default.",
        )

    async def probe_configuration(self, config: BeepConfig) -> ProviderProbeResult:
        from beep.agent.provider_probe_helpers import _build_model_probe_result

        headers: dict[str, str] = {}
        api_key = self._resolve_api_key(config)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            async with httpx.AsyncClient(
                base_url=self._resolve_base_url(config),
                headers=headers,
                timeout=httpx.Timeout(config.request_timeout, connect=10.0),
            ) as client:
                response = await client.get("/v1/models")
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

    def build_backend(
        self,
        config: BeepConfig,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> AgentModelBackend:
        del client
        del coding_assistant
        return OpenAICompatibleAgentBackend(
            base_url=self._resolve_base_url(config),
            api_key=self._resolve_api_key(config),
            model=config.effective_agent_model,
            request_timeout=config.request_timeout,
        )


class OllamaBackendProvider(LocalOpenAICompatibleProvider):
    """Built-in provider for Ollama's local OpenAI-compatible runtime."""

    key = "ollama"
    display_name = "Ollama"
    _default_base_url = "http://localhost:11434"

    def configuration_notes(self, config: BeepConfig) -> tuple[str, ...]:
        del config
        return (
            "Uses Ollama's local OpenAI-compatible server by default.",
            "Set agent_model to an installed Ollama model such as qwen2.5-coder or codellama.",
            "agent_api_key is optional for the default local Ollama runtime.",
        )

    def _build_capabilities(self) -> Any:
        return _default_capabilities(
            chat_description="Wraps Ollama's local OpenAI-compatible chat endpoint.",
            tool_description="Tool payloads are forwarded through the OpenAI-compatible transport; actual support depends on the selected Ollama model.",
            structured_output=True,
            structured_output_description="Forwards response_format through Ollama's OpenAI-compatible transport when the selected model/runtime supports it.",
            vision=True,
            vision_description="Preserves OpenAI-style multimodal message blocks such as image_url; actual vision support depends on the selected Ollama model/runtime.",
            local_runtime=True,
            local_runtime_description="Targets Ollama's local model runtime by default.",
        )

    async def probe_configuration(self, config: BeepConfig) -> ProviderProbeResult:
        from beep.agent.provider_probe_helpers import _build_model_probe_result

        headers: dict[str, str] = {}
        api_key = self._resolve_api_key(config)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            async with httpx.AsyncClient(
                base_url=self._resolve_base_url(config),
                headers=headers,
                timeout=httpx.Timeout(config.request_timeout, connect=10.0),
            ) as client:
                response = await client.get("/v1/models")
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

    def build_backend(
        self,
        config: BeepConfig,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> AgentModelBackend:
        del client
        del coding_assistant
        return OpenAICompatibleAgentBackend(
            base_url=self._resolve_base_url(config),
            api_key=self._resolve_api_key(config),
            model=config.effective_agent_model,
            request_timeout=config.request_timeout,
        )
