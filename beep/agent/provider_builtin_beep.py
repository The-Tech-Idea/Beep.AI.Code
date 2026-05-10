"""Built-in Beep.AI.Server provider for autonomous-agent backends."""

from __future__ import annotations

from typing import Any

from beep.agent.backends import AgentModelBackend, BeepAgentBackend
from beep.agent.provider_contracts import AgentBackendProvider, ProviderProbeResult
from beep.agent.provider_probe_helpers import _build_model_probe_result
from beep.agent.provider_capabilities import ProviderCapabilities, ProviderDescriptor
from beep.config import BeepConfig
from beep.runtime.capabilities import CapabilityFlag


class BeepBackendProvider(AgentBackendProvider):
    """Built-in provider for the canonical Beep.AI.Server surface."""

    key = "beep"
    display_name = "Beep.AI.Server"

    def requires_api_key(self) -> bool | None:
        return True

    def requires_model(self) -> bool | None:
        return False

    def configuration_notes(self, config: BeepConfig) -> tuple[str, ...]:
        del config
        return (
            "Uses server_url by default and falls back to api_token when agent_api_key is unset.",
            "Use this when the autonomous agent should target the canonical Beep.AI.Server surface.",
        )

    async def probe_configuration(self, config: BeepConfig) -> ProviderProbeResult:
        from beep.app_service import get_app_service

        client = get_app_service().api_client(config)
        try:
            models = await client.list_models()
            return _build_model_probe_result(models, selected_model=config.effective_agent_model)
        except Exception as exc:
            return ProviderProbeResult(
                supported=True,
                success=False,
                message=str(exc),
            )

    def is_configured(self, config: BeepConfig) -> bool:
        return bool(config.effective_agent_base_url) and config.effective_agent_api_key is not None

    def describe(self, config: BeepConfig) -> ProviderDescriptor:
        return ProviderDescriptor(
            key=self.key,
            display_name=self.display_name,
            capabilities=ProviderCapabilities(
                chat_completion=CapabilityFlag(
                    True,
                    "Uses the canonical Beep.AI.Server OpenAI-compatible chat surface.",
                ),
                tool_calling=CapabilityFlag(
                    True,
                    "Agent tools are passed through the Beep chat completion surface.",
                ),
                streaming=CapabilityFlag(
                    True,
                    "Streams Beep.AI.Server chat completion deltas through the autonomous agent runtime.",
                ),
                structured_output=CapabilityFlag(
                    True,
                    "Forwards response_format through the canonical Beep.AI.Server chat completion surface.",
                ),
                vision=CapabilityFlag(
                    True,
                    "Preserves OpenAI-style multimodal message blocks, including image_url inputs, through the canonical Beep.AI.Server chat surface.",
                ),
                embeddings=CapabilityFlag(
                    False,
                    "Embeddings are outside the autonomous agent backend contract.",
                ),
                local_model_runtime=CapabilityFlag(
                    False,
                    "Beep.AI.Server is a remote server/backend surface, not an in-process local runtime.",
                ),
            ),
        )

    def build_backend(
        self,
        config: BeepConfig,
        *,
        client: Any = None,
        coding_assistant: dict[str, Any] | None = None,
    ) -> AgentModelBackend:
        if client is None:
            from beep.app_service import get_app_service

            effective_client = get_app_service().api_client(config)
        else:
            effective_client = client
        return BeepAgentBackend(
            effective_client,
            model=config.effective_agent_model,
            coding_assistant=coding_assistant,
            owns_client=False,
        )
