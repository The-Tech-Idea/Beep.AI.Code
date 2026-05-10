"""Reusable helpers for plugin-authored agent backend providers."""

from __future__ import annotations

from typing import Any

import httpx

from beep.agent.backends import OpenAICompatibleAgentBackend
from beep.agent.provider_base import _default_capabilities
from beep.agent.provider_capabilities import ProviderDescriptor
from beep.agent.provider_contracts import ProviderProbeResult
from beep.config import BeepConfig
from beep.plugins.contracts import BackendProviderPlugin


class OpenAICompatibleProviderPluginBase(BackendProviderPlugin):
    """Base class for plugin-authored OpenAI-compatible backend providers."""

    provider_key_value: str = ""
    display_name: str = ""
    default_base_url_value: str | None = None
    requires_api_key_value: bool = True
    requires_model_value: bool = True
    local_runtime_value: bool = False
    chat_description: str = "Uses a plugin-authored OpenAI-compatible /v1/chat/completions API."
    tool_description: str = (
        "Tool payloads are forwarded through the OpenAI-compatible transport; actual support depends on the configured model/provider."
    )
    local_runtime_description: str = (
        "This plugin provider is not marked as an in-process local runtime."
    )

    def provider_key(self) -> str:
        return self.provider_key_value

    def requires_api_key(self) -> bool | None:
        return self.requires_api_key_value

    def requires_model(self) -> bool | None:
        return self.requires_model_value

    def default_base_url(self) -> str | None:
        return self.default_base_url_value

    def _resolve_base_url(self, config: BeepConfig) -> str:
        if config.agent_base_url and config.agent_base_url.strip():
            return config.agent_base_url.rstrip("/")
        if self.default_base_url_value is not None:
            return self.default_base_url_value.rstrip("/")
        return config.effective_agent_base_url

    def _resolve_api_key(self, config: BeepConfig) -> str | None:
        token = config.agent_api_key
        if token is None:
            return None
        return token.strip() or None

    def configuration_notes(self, config: Any) -> tuple[str, ...]:
        del config
        return (
            "Uses a plugin-authored OpenAI-compatible provider.",
            "Set agent_api_key and agent_model according to the provider's requirements.",
            "Set agent_base_url only when overriding the plugin's default endpoint.",
        )

    def is_configured(self, config: Any) -> bool:
        if not isinstance(config, BeepConfig):
            return False
        has_base_url = bool(self._resolve_base_url(config))
        has_api_key = self._resolve_api_key(config) is not None
        has_model = config.effective_agent_model is not None
        if self.requires_api_key_value and not has_api_key:
            return False
        if self.requires_model_value and not has_model:
            return False
        return has_base_url

    def describe(self, config: Any) -> Any:
        del config
        return ProviderDescriptor(
            key=self.provider_key(),
            display_name=self.display_name,
            capabilities=_default_capabilities(
                chat_description=self.chat_description,
                tool_description=self.tool_description,
                local_runtime=self.local_runtime_value,
                local_runtime_description=self.local_runtime_description,
            ),
        )

    async def probe_configuration(self, config: Any) -> ProviderProbeResult:
        if not isinstance(config, BeepConfig):
            return ProviderProbeResult(
                supported=False,
                success=False,
                message="Provider validation requires a BeepConfig instance.",
            )

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

        from beep.agent.provider_probe_helpers import _build_model_probe_result

        models = data.get("data", []) if isinstance(data, dict) else []
        return _build_model_probe_result(models, selected_model=config.effective_agent_model)

    def build_backend(
        self,
        config: Any,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> Any:
        del client
        del coding_assistant
        if not isinstance(config, BeepConfig):
            raise TypeError("Provider plugin backend construction requires a BeepConfig instance.")
        return OpenAICompatibleAgentBackend(
            base_url=self._resolve_base_url(config),
            api_key=self._resolve_api_key(config),
            model=config.effective_agent_model,
            request_timeout=config.request_timeout,
        )