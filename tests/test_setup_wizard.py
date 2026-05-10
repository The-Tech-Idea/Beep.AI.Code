"""Focused tests for setup wizard helpers."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.agent.provider_plugins import ProviderProbeResult
from beep.config import BeepConfig
from beep.setup_wizard import ensure_agent_configured, ensure_configured


def test_ensure_agent_configured_accepts_custom_provider_plugin() -> None:
    config = BeepConfig(agent_backend="custom-provider")
    plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_backend_provider=lambda key: SimpleNamespace(
                is_configured=lambda cfg: True,
                describe=lambda cfg: SimpleNamespace(
                    key="custom-provider",
                    display_name="Custom Provider",
                    capabilities=SimpleNamespace(local_model_runtime=SimpleNamespace(exists=False)),
                ),
                build_backend=lambda cfg, *, client=None, coding_assistant=None: None,
            ) if key == "custom-provider" else None
        )
    )

    with patch("beep.setup_wizard.load_config", return_value=config):
        with patch("beep.setup_wizard.find_workspace_root", return_value=SimpleNamespace()):
            with patch("beep.setup_wizard.load_runtime_plugins", return_value=plugin_runtime):
                assert ensure_agent_configured() is config


def test_ensure_agent_configured_rejects_unconfigured_custom_provider() -> None:
    config = BeepConfig(agent_backend="custom-provider")
    plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_backend_provider=lambda key: SimpleNamespace(
                is_configured=lambda cfg: False,
                describe=lambda cfg: SimpleNamespace(
                    key="custom-provider",
                    display_name="Custom Provider",
                    capabilities=SimpleNamespace(local_model_runtime=SimpleNamespace(exists=False)),
                ),
                build_backend=lambda cfg, *, client=None, coding_assistant=None: None,
            ) if key == "custom-provider" else None
        )
    )

    with patch("beep.setup_wizard.load_config", return_value=config):
        with patch("beep.setup_wizard.find_workspace_root", return_value=SimpleNamespace()):
            with patch("beep.setup_wizard.load_runtime_plugins", return_value=plugin_runtime):
                with pytest.raises(RuntimeError, match="custom-provider"):
                    ensure_agent_configured()


def test_ensure_agent_configured_runs_lm_studio_wizard() -> None:
    config = BeepConfig(agent_backend="lm-studio")
    plugin_runtime = SimpleNamespace(registry=SimpleNamespace())

    with patch("beep.setup_wizard.load_config", return_value=config):
        with patch("beep.setup_wizard.find_workspace_root", return_value=SimpleNamespace()):
            with patch("beep.setup_wizard.load_runtime_plugins", return_value=plugin_runtime):
                with patch("beep.setup_wizard.Prompt.ask", side_effect=["", "qwen-coder"]):
                    with patch(
                        "beep.setup_wizard.probe_agent_backend_configuration",
                        new=AsyncMock(
                            return_value=ProviderProbeResult(
                                supported=True,
                                success=True,
                                message="Connected to /v1/models. Found 1 models including 'qwen-coder'.",
                            )
                        ),
                    ):
                        with patch("beep.setup_wizard.save_config") as save_config_mock:
                            configured = ensure_agent_configured()

    assert configured.agent_backend == "lm-studio"
    assert configured.agent_base_url is None
    assert configured.agent_model == "qwen-coder"
    save_config_mock.assert_called_once_with(configured)


def test_ensure_agent_configured_runs_custom_provider_wizard_when_metadata_exists() -> None:
    config = BeepConfig(agent_backend="custom-provider")
    provider = SimpleNamespace(
        is_configured=lambda cfg: bool(cfg.agent_model),
        describe=lambda cfg: SimpleNamespace(
            key="custom-provider",
            display_name="Custom Provider",
            capabilities=SimpleNamespace(local_model_runtime=SimpleNamespace(exists=False)),
        ),
        source_label=lambda: "plugin",
        requires_api_key=lambda: False,
        requires_model=lambda: True,
        default_base_url=lambda: "http://plugin.test",
        configuration_notes=lambda cfg: ("Set agent_model before use.",),
        build_backend=lambda cfg, *, client=None, coding_assistant=None: None,
    )
    plugin_runtime = SimpleNamespace(
        registry=SimpleNamespace(
            get_backend_provider=lambda key: provider if key == "custom-provider" else None,
            list_backend_providers=lambda: ["custom-provider"],
        )
    )

    with patch("beep.setup_wizard.load_config", return_value=config):
        with patch("beep.setup_wizard.find_workspace_root", return_value=SimpleNamespace()):
            with patch("beep.setup_wizard.load_runtime_plugins", return_value=plugin_runtime):
                with patch("beep.setup_wizard.Prompt.ask", side_effect=["", "model-x"]):
                    with patch(
                        "beep.setup_wizard.probe_agent_backend_configuration",
                        new=AsyncMock(
                            return_value=ProviderProbeResult(
                                supported=False,
                                success=False,
                                message="This provider does not expose a validation probe.",
                            )
                        ),
                    ):
                        with patch("beep.setup_wizard.save_config") as save_config_mock:
                            configured = ensure_agent_configured()

    assert configured.agent_backend == "custom-provider"
    assert configured.agent_base_url is None
    assert configured.agent_model == "model-x"
    save_config_mock.assert_called_once_with(configured)


def test_ensure_agent_configured_cancels_when_provider_probe_fails() -> None:
    config = BeepConfig(agent_backend="lm-studio")
    plugin_runtime = SimpleNamespace(registry=SimpleNamespace())

    with patch("beep.setup_wizard.load_config", return_value=config):
        with patch("beep.setup_wizard.find_workspace_root", return_value=SimpleNamespace()):
            with patch("beep.setup_wizard.load_runtime_plugins", return_value=plugin_runtime):
                with patch("beep.setup_wizard.Prompt.ask", side_effect=["", "qwen-coder", "n"]):
                    with patch(
                        "beep.setup_wizard.probe_agent_backend_configuration",
                        new=AsyncMock(
                            return_value=ProviderProbeResult(
                                supported=True,
                                success=False,
                                message="Connected to /v1/models, but model 'qwen-coder' was not returned.",
                            )
                        ),
                    ):
                        with patch("beep.setup_wizard.save_config") as save_config_mock:
                            with pytest.raises(SystemExit):
                                ensure_agent_configured()

    save_config_mock.assert_not_called()


def _make_mock_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


class TestEnsureConfigured:
    def test_returns_config_when_token_set(self) -> None:
        token_config = BeepConfig(
            server_url="http://localhost:5000",
            api_token="test-token",
        )
        with patch("beep.setup_wizard.load_config", return_value=token_config):
            config = ensure_configured()
            assert config.api_token == "test-token"

    def test_returns_config_when_env_vars_set(self) -> None:
        env_config = BeepConfig(
            server_url="http://test",
            api_token="env-token",
        )
        with patch.dict(
            os.environ,
            {"BEEP_API_TOKEN": "env-token", "BEEP_SERVER_URL": "http://test"},
        ):
            with patch("beep.setup_wizard.load_config", return_value=env_config):
                config = ensure_configured()
                assert config.api_token == "env-token"

    def test_exits_when_not_configured_and_user_declines(self) -> None:
        unconfigured = BeepConfig(server_url="http://localhost:5000")
        with patch("beep.setup_wizard.load_config", return_value=unconfigured), \
             patch("beep.setup_wizard.Prompt.ask", return_value="n"):
            with pytest.raises(SystemExit):
                ensure_configured()


class TestConnectionTest:
    @pytest.mark.asyncio
    async def test_connection_success(self) -> None:
        from beep.setup_wizard import _test_connection

        mock_client = AsyncMock()
        mock_client.health_check = AsyncMock(return_value={"status": "ok"})
        mock_client.close = AsyncMock()

        config = BeepConfig(server_url="http://test", api_token="token")
        with patch("beep.setup_wizard.BeepAPIClient", return_value=mock_client):
            success, message = await _test_connection(config)
            assert success is True
            assert "ok" in message

    @pytest.mark.asyncio
    async def test_connection_failure(self) -> None:
        from beep.setup_wizard import _test_connection

        mock_client = AsyncMock()
        mock_client.health_check = AsyncMock(side_effect=ConnectionError("refused"))
        mock_client.close = AsyncMock()

        config = BeepConfig(server_url="http://test", api_token="token")
        with patch("beep.setup_wizard.BeepAPIClient", return_value=mock_client):
            success, message = await _test_connection(config)
            assert success is False
            assert "refused" in message


class TestTokenValidation:
    @pytest.mark.asyncio
    async def test_token_valid(self) -> None:
        from beep.setup_wizard import _test_token

        mock_client = AsyncMock()
        mock_client.check_token = AsyncMock(return_value={
            "valid": True,
            "application": {"name": "test-app"},
            "scopes": ["llm:write", "rag:read"],
        })
        mock_client.close = AsyncMock()

        config = BeepConfig(server_url="http://test", api_token="token")
        with patch("beep.setup_wizard.BeepAPIClient", return_value=mock_client):
            success, message = await _test_token(config)
            assert success is True
            assert "test-app" in message
            assert "llm:write" in message

    @pytest.mark.asyncio
    async def test_token_invalid(self) -> None:
        from beep.setup_wizard import _test_token

        mock_client = AsyncMock()
        mock_client.check_token = AsyncMock(return_value={
            "valid": False,
            "error": "Token expired",
        })
        mock_client.close = AsyncMock()

        config = BeepConfig(server_url="http://test", api_token="token")
        with patch("beep.setup_wizard.BeepAPIClient", return_value=mock_client):
            success, message = await _test_token(config)
            assert success is False
            assert "expired" in message
