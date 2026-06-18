"""Tests for local and gateway providers (Ollama, LM Studio, LiteLLM)."""

from __future__ import annotations

from beep.agent.provider_plugins import _BUILTIN_AGENT_BACKEND_PROVIDERS


class TestLocalProviders:
    def test_ollama_registered(self) -> None:
        assert "ollama" in _BUILTIN_AGENT_BACKEND_PROVIDERS
        provider = _BUILTIN_AGENT_BACKEND_PROVIDERS["ollama"]
        assert provider.key == "ollama"
        assert not provider.requires_api_key()

    def test_lm_studio_registered(self) -> None:
        assert "lm-studio" in _BUILTIN_AGENT_BACKEND_PROVIDERS
        provider = _BUILTIN_AGENT_BACKEND_PROVIDERS["lm-studio"]
        assert provider.key == "lm-studio"
        assert not provider.requires_api_key()

    def test_litellm_registered(self) -> None:
        assert "litellm" in _BUILTIN_AGENT_BACKEND_PROVIDERS
        provider = _BUILTIN_AGENT_BACKEND_PROVIDERS["litellm"]
        assert provider.key == "litellm"
        assert provider.display_name == "LiteLLM"

    def test_ollama_default_url(self) -> None:
        provider = _BUILTIN_AGENT_BACKEND_PROVIDERS["ollama"]
        url = provider.default_base_url() or ""
        assert "11434" in url

    def test_litellm_default_url(self) -> None:
        provider = _BUILTIN_AGENT_BACKEND_PROVIDERS["litellm"]
        url = provider.default_base_url() or ""
        assert "4000" in url


class TestProviderListing:
    def test_provider_count(self) -> None:
        assert len(_BUILTIN_AGENT_BACKEND_PROVIDERS) >= 8

    def test_all_providers_have_keys(self) -> None:
        for key, provider in _BUILTIN_AGENT_BACKEND_PROVIDERS.items():
            assert provider.key == key
            assert provider.display_name

    def test_local_providers_in_listing(self) -> None:
        keys = set(_BUILTIN_AGENT_BACKEND_PROVIDERS.keys())
        assert "ollama" in keys
        assert "lm-studio" in keys
        assert "litellm" in keys
