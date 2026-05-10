"""Tests for the central AppService registry."""

from __future__ import annotations

import pytest

from beep.app_service import AppService, get_app_service
from beep.codeanalysis.service import CodeAnalysisService
from beep.watcher.service import WatcherService
from beep.bookmarks.manager import BookmarkManager
from beep.tasks.manager import TaskManager
from beep.permissions.manager import PermissionManager
from beep.hooks.manager import HookConfig


class TestAppServiceSingleton:
    """Verify that AppService itself and all managed services are singletons."""

    def setup_method(self) -> None:
        """Reset the global registry before each test."""
        AppService.reset_registry()

    def teardown_method(self) -> None:
        """Reset the global registry after each test."""
        AppService.reset_registry()

    def test_app_service_is_singleton(self) -> None:
        s1 = get_app_service()
        s2 = get_app_service()
        assert s1 is s2
        assert isinstance(s1, AppService)

    def test_code_analysis_singleton(self) -> None:
        app = get_app_service()
        ca1 = app.code_analysis
        ca2 = app.code_analysis
        assert ca1 is ca2
        assert isinstance(ca1, CodeAnalysisService)

    def test_bookmarks_singleton(self) -> None:
        app = get_app_service()
        bm1 = app.bookmarks
        bm2 = app.bookmarks
        assert bm1 is bm2
        assert isinstance(bm1, BookmarkManager)

    def test_tasks_singleton(self) -> None:
        app = get_app_service()
        tm1 = app.tasks
        tm2 = app.tasks
        assert tm1 is tm2
        assert isinstance(tm1, TaskManager)

    def test_permissions_singleton(self) -> None:
        app = get_app_service()
        pm1 = app.permissions
        pm2 = app.permissions
        assert pm1 is pm2
        assert isinstance(pm1, PermissionManager)

    def test_hooks_singleton(self) -> None:
        app = get_app_service()
        hc1 = app.hooks
        hc2 = app.hooks
        assert hc1 is hc2
        assert isinstance(hc1, HookConfig)

    def test_watcher_keyed_singleton_same_root(self) -> None:
        app = get_app_service()
        w1 = app.watcher("/tmp")
        w2 = app.watcher("/tmp")
        assert w1 is w2
        assert isinstance(w1, WatcherService)

    def test_watcher_different_roots_are_different(self) -> None:
        app = get_app_service()
        w1 = app.watcher("/tmp/a")
        w2 = app.watcher("/tmp/b")
        assert w1 is not w2

    def test_reset_clears_singletons(self) -> None:
        app = get_app_service()
        ca1 = app.code_analysis
        app.reset()
        # After reset, accessing the property creates a new instance
        ca2 = app.code_analysis
        assert ca1 is not ca2

    def test_reset_registry_clears_everything(self) -> None:
        s1 = get_app_service()
        AppService.reset_registry()
        s2 = get_app_service()
        assert s1 is not s2

    def test_language_registry_singleton(self) -> None:
        app = get_app_service()
        lr1 = app.language_registry
        lr2 = app.language_registry
        assert lr1 is lr2

    def test_template_registry_singleton(self) -> None:
        app = get_app_service()
        tr1 = app.template_registry
        tr2 = app.template_registry
        assert tr1 is tr2
        # Verify plugins were registered
        assert len(tr1._plugins) > 0

    def test_api_client_singleton_same_config(self) -> None:
        from beep.config import BeepConfig

        app = get_app_service()
        config = BeepConfig(server_url="http://test", api_token="token123")
        c1 = app.api_client(config)
        c2 = app.api_client(config)
        assert c1 is c2

    def test_api_client_different_configs_are_different(self) -> None:
        from beep.config import BeepConfig

        app = get_app_service()
        config1 = BeepConfig(server_url="http://test1", api_token="token1")
        config2 = BeepConfig(server_url="http://test2", api_token="token2")
        c1 = app.api_client(config1)
        c2 = app.api_client(config2)
        assert c1 is not c2

    def test_smart_context_singleton(self) -> None:
        app = get_app_service()
        sc1 = app.smart_context("/tmp")
        sc2 = app.smart_context("/tmp")
        assert sc1 is sc2

    def test_auto_context_singleton(self) -> None:
        app = get_app_service()
        ac1 = app.auto_context("/tmp")
        ac2 = app.auto_context("/tmp")
        assert ac1 is ac2

    def test_chat_context_singleton(self) -> None:
        app = get_app_service()
        cc1 = app.chat_context("/tmp")
        cc2 = app.chat_context("/tmp")
        assert cc1 is cc2

    def test_chat_context_different_workspaces(self) -> None:
        app = get_app_service()
        cc1 = app.chat_context("/tmp/a")
        cc2 = app.chat_context("/tmp/b")
        assert cc1 is not cc2

    def test_tree_sitter_parser_singleton(self) -> None:
        app = get_app_service()
        p1 = app.tree_sitter_parser
        p2 = app.tree_sitter_parser
        assert p1 is p2

    def test_python_jedi_singleton(self) -> None:
        app = get_app_service()
        pj1 = app.python_jedi("/tmp")
        pj2 = app.python_jedi("/tmp")
        assert pj1 is pj2

    def test_semble_index_singleton(self) -> None:
        app = get_app_service()
        si1 = app.semble_index("/tmp")
        si2 = app.semble_index("/tmp")
        assert si1 is si2

    def test_plugin_registry_singleton(self) -> None:
        app = get_app_service()
        pr1 = app.plugin_registry("/tmp")
        pr2 = app.plugin_registry("/tmp")
        assert pr1 is pr2

    def test_template_validator_singleton(self) -> None:
        app = get_app_service()
        tv1 = app.template_validator
        tv2 = app.template_validator
        assert tv1 is tv2

    def test_rollback_singleton(self) -> None:
        app = get_app_service()
        r1 = app.rollback
        r2 = app.rollback
        assert r1 is r2

    def test_standards_reviewer_singleton(self) -> None:
        app = get_app_service()
        sr1 = app.standards_reviewer
        sr2 = app.standards_reviewer
        assert sr1 is sr2
