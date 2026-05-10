"""Configuration management for Beep.AI.Code."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


CONFIG_SCHEMA_VERSION = 1


class MCPToolConfig(BaseModel):
    """Tool declaration for an MCP server entry in config."""

    name: str
    description: str = ""
    parameters: dict = Field(default_factory=dict)
    read_only_safe: bool = Field(
        default=False,
        description="Whether the tool may be exposed in read-only agent mode.",
    )
    requires_human_approval: bool = Field(
        default=True,
        description="Whether the tool should remain behind the human approval gate.",
    )


class MCPServerConfig(BaseModel):
    """MCP server declaration for optional local tool bridging."""

    name: str
    transport: Literal["stdio", "http"] = Field(default="stdio")
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    tools: list[MCPToolConfig] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_transport_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        transport = payload.get("transport", payload.get("type"))
        if isinstance(transport, str):
            normalized_transport = transport.strip().lower()
            if normalized_transport == "streamable-http":
                normalized_transport = "http"
            payload["transport"] = normalized_transport
        if payload.get("url") is None:
            server_url = payload.get("serverUrl") or payload.get("endpoint")
            if isinstance(server_url, str) and server_url.strip():
                payload["url"] = server_url.strip()
        return payload

    @model_validator(mode="after")
    def _validate_transport_shape(self) -> MCPServerConfig:
        if self.transport == "stdio":
            if not self.command or not self.command.strip():
                raise ValueError("stdio MCP servers require a non-empty command")
            return self
        if not self.url or not self.url.strip():
            raise ValueError("http MCP servers require a non-empty url")
        return self


class BeepConfig(BaseModel):
    """Configuration for Beep.AI.Code CLI."""

    schema_version: int = Field(
        default=CONFIG_SCHEMA_VERSION,
        ge=1,
        description="Persisted Beep.AI.Code config schema version",
    )

    server_url: str = Field(default="http://localhost:5000", description="Beep.AI.Server URL")
    api_token: str | None = Field(default=None, description="API authentication token")
    default_model: str | None = Field(default=None, description="Default model ID")
    agent_backend: str = Field(
        default="beep",
        description="Backend used by the autonomous coding agent",
    )
    agent_base_url: str | None = Field(
        default=None,
        description="Optional base URL override used by the autonomous coding agent",
    )
    agent_api_key: str | None = Field(
        default=None,
        description="Optional API key override used by the autonomous coding agent",
    )
    agent_model: str | None = Field(
        default=None,
        description="Optional model override used by the autonomous coding agent",
    )
    agent_reasoning_effort: str | None = Field(
        default=None,
        description="Optional reasoning effort hint for compatible autonomous-agent backends",
    )
    agent_parallel_tool_calls: bool | None = Field(
        default=None,
        description="Optional parallel_tool_calls override for compatible autonomous-agent backends",
    )
    agent_thinking_budget_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Optional Anthropic thinking budget for compatible autonomous-agent backends",
    )
    max_tokens: int = Field(default=4096, ge=1, le=128000, description="Max tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    project_id: int | None = Field(default=None, description="Coding Assistant project ID")
    mcp_enabled: bool = Field(default=False, description="Enable optional MCP bridge")
    mcp_servers: list[MCPServerConfig] = Field(
        default_factory=list,
        description="Configured MCP servers for optional bridge",
    )
    request_timeout: float = Field(
        default=60.0, ge=1.0, description="HTTP request timeout in seconds"
    )
    retry_on_429: bool = Field(
        default=True, description="Retry requests on HTTP 429 / 503 responses"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts for transient errors"
    )

    @property
    def is_configured(self) -> bool:
        return self.api_token is not None and bool(self.api_token.strip())

    @property
    def effective_agent_base_url(self) -> str:
        """Return the resolved base URL for the autonomous agent backend."""
        return (self.agent_base_url or self.server_url).rstrip("/")

    @property
    def effective_agent_api_key(self) -> str | None:
        """Return the resolved API key for the autonomous agent backend."""
        token = self.agent_api_key if self.agent_api_key is not None else self.api_token
        if token is None:
            return None
        return token.strip() or None

    @property
    def effective_agent_model(self) -> str | None:
        """Return the resolved model for the autonomous agent backend."""
        model = self.agent_model if self.agent_model is not None else self.default_model
        if model is None:
            return None
        return model.strip() or None

    @property
    def is_agent_configured(self) -> bool:
        """Return True when the autonomous agent backend has enough configuration."""
        try:
            from beep.agent.provider_plugins import is_agent_backend_configured

            return is_agent_backend_configured(self)
        except ValueError:
            return False


CONFIG_DIR = Path.home() / ".beepai"
CONFIG_FILE = CONFIG_DIR / "code.json"


def _load_raw_config_file() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as file_handle:
            raw = json.load(file_handle)
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _migrate_config_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    data = dict(payload)
    migrated = False
    schema_version = data.get("schema_version")

    if not isinstance(schema_version, int):
        data["schema_version"] = CONFIG_SCHEMA_VERSION
        migrated = True
    elif schema_version < CONFIG_SCHEMA_VERSION:
        data["schema_version"] = CONFIG_SCHEMA_VERSION
        migrated = True

    if "model" in data and "default_model" not in data:
        data["default_model"] = data.pop("model")
        migrated = True

    return data, migrated


def _write_raw_config_file(payload: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)
    os.chmod(CONFIG_FILE, 0o600)


def load_config() -> BeepConfig:
    """Load configuration from file and environment variables."""
    data = _load_raw_config_file()
    data, migrated = _migrate_config_payload(data)
    if migrated and data:
        try:
            _write_raw_config_file(data)
        except OSError:
            pass

    env_url = os.environ.get("BEEP_SERVER_URL")
    if env_url:
        data["server_url"] = env_url

    env_token = os.environ.get("BEEP_API_TOKEN")
    if env_token:
        data["api_token"] = env_token

    env_model = os.environ.get("BEEP_DEFAULT_MODEL")
    if env_model:
        data["default_model"] = env_model

    env_agent_backend = os.environ.get("BEEP_AGENT_BACKEND")
    if env_agent_backend:
        data["agent_backend"] = env_agent_backend

    env_agent_base_url = os.environ.get("BEEP_AGENT_BASE_URL")
    if env_agent_base_url:
        data["agent_base_url"] = env_agent_base_url

    env_agent_api_key = os.environ.get("BEEP_AGENT_API_KEY")
    if env_agent_api_key:
        data["agent_api_key"] = env_agent_api_key

    env_agent_model = os.environ.get("BEEP_AGENT_MODEL")
    if env_agent_model:
        data["agent_model"] = env_agent_model

    env_agent_reasoning_effort = os.environ.get("BEEP_AGENT_REASONING_EFFORT")
    if env_agent_reasoning_effort:
        data["agent_reasoning_effort"] = env_agent_reasoning_effort

    env_agent_parallel_tool_calls = os.environ.get("BEEP_AGENT_PARALLEL_TOOL_CALLS")
    if env_agent_parallel_tool_calls:
        data["agent_parallel_tool_calls"] = env_agent_parallel_tool_calls.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    env_agent_thinking_budget_tokens = os.environ.get("BEEP_AGENT_THINKING_BUDGET_TOKENS")
    if env_agent_thinking_budget_tokens:
        data["agent_thinking_budget_tokens"] = int(env_agent_thinking_budget_tokens)

    env_project_id = os.environ.get("BEEP_PROJECT_ID")
    if env_project_id:
        data["project_id"] = int(env_project_id)

    env_mcp = os.environ.get("BEEP_MCP")
    if env_mcp:
        data["mcp_enabled"] = env_mcp.strip().lower() in {"1", "true", "yes", "on"}

    return BeepConfig(**data)


def save_config(config: BeepConfig) -> None:
    """Save configuration to file."""
    data = config.model_dump(exclude_none=True)
    data["schema_version"] = CONFIG_SCHEMA_VERSION
    _write_raw_config_file(data)


def get_config_path() -> Path:
    """Return the config file path."""
    return CONFIG_FILE
