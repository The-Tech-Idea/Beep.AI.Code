"""Tests for configuration management."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from beep.config import CONFIG_SCHEMA_VERSION, BeepConfig, load_config, save_config


@pytest.fixture
def temp_config_dir():
    """Use a temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "code.json"
        with patch("beep.config.CONFIG_FILE", tmp_path):
            yield tmp_path


def test_default_config():
    """Test default configuration values."""
    config = BeepConfig()
    assert config.schema_version == CONFIG_SCHEMA_VERSION
    assert config.server_url == "http://localhost:5000"
    assert config.api_token is None
    assert config.default_model is None
    assert config.agent_backend == "beep"
    assert config.agent_base_url is None
    assert config.agent_api_key is None
    assert config.agent_model is None
    assert config.max_tokens == 4096
    assert config.temperature == 0.7
    assert config.mcp_enabled is False
    assert config.mcp_servers == []
    assert not config.is_configured
    assert not config.is_agent_configured


def test_config_with_token():
    """Test config is configured when token is set."""
    config = BeepConfig(api_token="test-token-123")
    assert config.is_configured
    assert config.is_agent_configured


def test_save_and_load_config(temp_config_dir):
    """Test saving and loading configuration."""
    config = BeepConfig(
        server_url="http://test:5000",
        api_token="test-token",
        default_model="gpt-4",
        max_tokens=8192,
        temperature=0.5,
    )
    save_config(config)

    assert temp_config_dir.exists()
    persisted = temp_config_dir.read_text(encoding="utf-8")
    assert '"schema_version": 1' in persisted
    loaded = load_config()
    assert loaded.schema_version == CONFIG_SCHEMA_VERSION
    assert loaded.server_url == "http://test:5000"
    assert loaded.api_token == "test-token"
    assert loaded.default_model == "gpt-4"
    assert loaded.max_tokens == 8192
    assert loaded.temperature == 0.5


def test_env_var_overrides(temp_config_dir):
    """Test environment variable overrides."""
    with patch.dict(
        os.environ,
        {
            "BEEP_SERVER_URL": "http://env:5000",
            "BEEP_API_TOKEN": "env-token",
            "BEEP_DEFAULT_MODEL": "claude-3",
            "BEEP_AGENT_BACKEND": "openai-compatible",
            "BEEP_AGENT_BASE_URL": "http://openai.example",
            "BEEP_AGENT_API_KEY": "agent-token",
            "BEEP_AGENT_MODEL": "gpt-4.1-mini",
            "BEEP_PROJECT_ID": "42",
            "BEEP_MCP": "1",
        },
    ):
        config = load_config()
        assert config.server_url == "http://env:5000"
        assert config.api_token == "env-token"
        assert config.default_model == "claude-3"
        assert config.agent_backend == "openai-compatible"
        assert config.agent_base_url == "http://openai.example"
        assert config.agent_api_key == "agent-token"
        assert config.agent_model == "gpt-4.1-mini"
        assert config.project_id == 42
        assert config.mcp_enabled is True


def test_agent_effective_values_prefer_agent_overrides() -> None:
    config = BeepConfig(
        server_url="http://beep-server",
        api_token="beep-token",
        default_model="beep-model",
        agent_backend="openai-compatible",
        agent_base_url="http://other-provider",
        agent_api_key="other-token",
        agent_model="other-model",
    )
    assert config.effective_agent_base_url == "http://other-provider"
    assert config.effective_agent_api_key == "other-token"
    assert config.effective_agent_model == "other-model"
    assert config.is_agent_configured


def test_is_agent_configured_uses_provider_registry_for_openai_and_local_providers() -> None:
    openai_config = BeepConfig(
        agent_backend="openai",
        agent_api_key="openai-token",
        agent_model="gpt-4.1-mini",
    )
    anthropic_config = BeepConfig(
        agent_backend="anthropic",
        agent_api_key="anthropic-token",
        agent_model="claude-sonnet-4-20250514",
    )
    openrouter_config = BeepConfig(
        agent_backend="openrouter",
        agent_api_key="openrouter-token",
        agent_model="anthropic/claude-sonnet-4",
    )
    lm_studio_config = BeepConfig(agent_backend="lm-studio", agent_model="qwen-coder")

    assert openai_config.is_agent_configured is True
    assert anthropic_config.is_agent_configured is True
    assert openrouter_config.is_agent_configured is True
    assert lm_studio_config.is_agent_configured is True


def test_config_file_permissions(temp_config_dir):
    """Test config file is saved with restrictive permissions."""
    config = BeepConfig(api_token="secret")
    save_config(config)

    if os.name != "nt":
        mode = oct(temp_config_dir.stat().st_mode)[-3:]
        assert mode == "600"


def test_invalid_json_config(temp_config_dir):
    """Test loading handles invalid JSON gracefully."""
    temp_config_dir.write_text("not valid json")
    config = load_config()
    assert config.schema_version == CONFIG_SCHEMA_VERSION
    assert config.server_url == "http://localhost:5000"


def test_load_legacy_config_adds_schema_version_and_persists_migration(temp_config_dir):
    temp_config_dir.write_text(
        json.dumps(
            {
                "server_url": "http://legacy:5000",
                "api_token": "legacy-token",
                "default_model": "legacy-model",
            }
        ),
        encoding="utf-8",
    )

    config = load_config()

    assert config.schema_version == CONFIG_SCHEMA_VERSION
    assert config.server_url == "http://legacy:5000"
    persisted = temp_config_dir.read_text(encoding="utf-8")
    assert '"schema_version": 1' in persisted


def test_load_legacy_model_key_migrates_to_default_model(temp_config_dir):
    temp_config_dir.write_text(
        json.dumps(
            {
                "server_url": "http://legacy:5000",
                "model": "legacy-model",
            }
        ),
        encoding="utf-8",
    )

    config = load_config()

    assert config.default_model == "legacy-model"
    persisted = temp_config_dir.read_text(encoding="utf-8")
    assert '"default_model": "legacy-model"' in persisted
    assert '"model"' not in persisted


def test_load_mcp_servers_from_file(temp_config_dir):
    temp_config_dir.write_text(
        """
{
  "server_url": "http://localhost:5000",
  "mcp_enabled": true,
  "mcp_servers": [
    {
      "name": "local-mcp",
      "command": "python",
      "args": ["-m", "mcp_server"],
      "tools": [
        {"name": "query_db", "description": "Query DB", "parameters": {"type": "object"}}
      ]
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    config = load_config()
    assert config.mcp_enabled is True
    assert len(config.mcp_servers) == 1
    assert config.mcp_servers[0].name == "local-mcp"
    assert config.mcp_servers[0].tools[0].name == "query_db"
