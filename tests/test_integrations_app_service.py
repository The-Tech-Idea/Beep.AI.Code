"""Tests for IntegrationsRegistry in AppService."""

from __future__ import annotations

import pytest

from beep.app_service import AppService, get_app_service


class TestAppServiceIntegrations:
    def test_property_returns_registry(self) -> None:
        app = get_app_service()
        registry = app.integrations
        assert registry is not None

    def test_singleton_identity(self) -> None:
        app = get_app_service()
        r1 = app.integrations
        r2 = app.integrations
        assert r1 is r2

    def test_find_entry(self) -> None:
        app = get_app_service()
        entry = app.integrations.find("graphify")
        assert entry is not None
        assert entry.id == "graphify"

    def test_search_entries(self) -> None:
        app = get_app_service()
        results = app.integrations.search("test")
        assert len(results) > 0

    def test_list_installed_initially_empty(self) -> None:
        app = get_app_service()
        installed = app.integrations.list_installed()
        assert isinstance(installed, list)

    def test_is_installed_initially_false(self) -> None:
        app = get_app_service()
        assert app.integrations.is_installed("graphify") is False

    def test_reset_clears(self, monkeypatch: pytest.MonkeyPatch) -> None:
        app = get_app_service()
        _ = app.integrations
        app.reset()
        assert app._integrations is None
