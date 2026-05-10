"""Central application service registry.

All Beep services and managers are owned as singletons by :class:`AppService`.
This is the single source of truth for service instances.  Code should never
instantiate service classes directly; instead it should call
:func:`get_app_service` and access the required manager through a property.

Example::

    from beep.app_service import get_app_service

    app = get_app_service()
    app.code_analysis.analyze_project("/path/to/project")
    app.bookmarks.add("myfile", Path("/path"))

The registry is itself a singleton: :func:`get_app_service` always returns the
same instance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beep.bookmarks.manager import BookmarkManager
    from beep.codeanalysis.service import CodeAnalysisService
    from beep.hooks.manager import HookConfig
    from beep.permissions.manager import PermissionManager
    from beep.tasks.manager import TaskManager
    from beep.watcher.service import WatcherService


class AppService:
    """Central registry for all Beep singleton services.

    Each property lazily creates and caches the underlying service so that
    the same instance is returned for the lifetime of the process.
    """

    _instance: AppService | None = None

    def __new__(cls) -> AppService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        # Simple singletons (no init args)
        self._code_analysis: CodeAnalysisService | None = None
        self._bookmarks: BookmarkManager | None = None
        self._tasks: TaskManager | None = None
        self._permissions: PermissionManager | None = None
        self._hooks: HookConfig | None = None
        self._language_registry: Any | None = None
        self._template_registry: Any | None = None

        # Keyed singletons (cache by key)
        self._watchers: dict[str, WatcherService] = {}
        self._api_clients: dict[str, Any] = {}
        self._mcp_clients: dict[str, Any] = {}
        self._smart_contexts: dict[str, Any] = {}
        self._auto_contexts: dict[str, Any] = {}
        self._chat_contexts: dict[str, Any] = {}
        self._tree_sitter_parser: Any | None = None
        self._python_jedi_adapters: dict[str, Any] = {}
        self._semble_index_adapters: dict[str, Any] = {}
        self._plugin_registries: dict[str, Any] = {}
        self._template_validator: Any | None = None
        self._rollback_manager: Any | None = None
        self._standards_reviewer: Any | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def code_analysis(self) -> CodeAnalysisService:
        """Return the singleton :class:`CodeAnalysisService`."""
        if self._code_analysis is None:
            from beep.codeanalysis.service import CodeAnalysisService

            self._code_analysis = CodeAnalysisService()
        return self._code_analysis

    @property
    def bookmarks(self) -> BookmarkManager:
        """Return the singleton :class:`BookmarkManager`, loading from disk."""
        if self._bookmarks is None:
            from beep.bookmarks.manager import BookmarkManager

            self._bookmarks = BookmarkManager.load()
        return self._bookmarks

    @property
    def tasks(self) -> TaskManager:
        """Return the singleton :class:`TaskManager`."""
        if self._tasks is None:
            from beep.tasks.manager import TaskManager

            self._tasks = TaskManager()
        return self._tasks

    @property
    def permissions(self) -> PermissionManager:
        """Return the singleton :class:`PermissionManager`."""
        if self._permissions is None:
            from beep.permissions.manager import PermissionManager

            self._permissions = PermissionManager()
        return self._permissions

    @property
    def hooks(self) -> HookConfig:
        """Return the singleton :class:`HookConfig`, loading from disk."""
        if self._hooks is None:
            from beep.hooks.manager import load_hooks

            self._hooks = load_hooks()
        return self._hooks

    @property
    def language_registry(self) -> Any:
        """Return the singleton :class:`LanguageRegistry`."""
        if self._language_registry is None:
            from beep.languages.registry import LanguageRegistry

            self._language_registry = LanguageRegistry()
        return self._language_registry

    @property
    def template_registry(self) -> Any:
        """Return the singleton :class:`ProjectTemplateRegistry`."""
        if self._template_registry is None:
            from beep.templates.registry import ProjectTemplateRegistry
            from beep.templates.plugins import BUILTIN_PLUGINS

            self._template_registry = ProjectTemplateRegistry()
            for plugin in BUILTIN_PLUGINS:
                self._template_registry.register(plugin)
        return self._template_registry

    def watcher(self, root: Path | str) -> WatcherService:
        """Return the singleton :class:`WatcherService` for *root*.

        One instance is cached per resolved root path.
        """
        key = str(Path(root).resolve())
        if key not in self._watchers:
            from beep.watcher.service import WatcherService

            self._watchers[key] = WatcherService(root=Path(root))
        return self._watchers[key]

    def api_client(self, config: Any) -> Any:
        """Return the singleton :class:`BeepAPIClient` for *config*.

        One instance is cached per unique config (server_url + api_token).
        The client is **not** closed after each use; it is reused across
        the process lifetime and closed when :meth:`reset` is called.
        """
        from beep.api.client import BeepAPIClient

        key = f"{config.server_url}:{config.api_token or 'no-token'}"
        if key not in self._api_clients:
            self._api_clients[key] = BeepAPIClient(config)
        return self._api_clients[key]

    def mcp_client(self, servers: list[Any]) -> Any:
        """Return the singleton :class:`MCPClient` for *servers*.

        One instance is cached per unique server configuration.
        """
        from beep.mcp.client import MCPClient
        import json

        key = json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in servers],
            sort_keys=True,
        )
        if key not in self._mcp_clients:
            self._mcp_clients[key] = MCPClient.from_config(servers)
        return self._mcp_clients[key]

    def smart_context(self, workspace_root: Path | str) -> Any:
        """Return the singleton :class:`SmartContextBuilder` for *workspace_root*."""
        from beep.context.smart import SmartContextBuilder

        key = str(Path(workspace_root).resolve())
        if key not in self._smart_contexts:
            self._smart_contexts[key] = SmartContextBuilder(Path(workspace_root))
        return self._smart_contexts[key]

    def auto_context(self, workspace_root: Path | str) -> Any:
        """Return the singleton :class:`AutoContextBuilder` for *workspace_root*."""
        from beep.context.auto_context import AutoContextBuilder

        key = str(Path(workspace_root).resolve())
        if key not in self._auto_contexts:
            self._auto_contexts[key] = AutoContextBuilder(workspace_root)
        return self._auto_contexts[key]

    def chat_context(self, workspace_root: Path | str) -> Any:
        """Return the singleton :class:`ChatContext` for *workspace_root*.

        Pinned files are shared across all sessions for the same workspace.
        """
        from beep.chat.context import ChatContext

        key = str(Path(workspace_root).resolve())
        if key not in self._chat_contexts:
            self._chat_contexts[key] = ChatContext(Path(workspace_root))
        return self._chat_contexts[key]

    @property
    def tree_sitter_parser(self) -> Any:
        """Return the singleton :class:`TreeSitterParser`."""
        if self._tree_sitter_parser is None:
            from beep.codeindex.tree_sitter_parser import TreeSitterParser

            self._tree_sitter_parser = TreeSitterParser()
        return self._tree_sitter_parser

    def python_jedi(self, workspace_root: Path | str) -> Any:
        """Return the singleton :class:`PythonJediAdapter` for *workspace_root*."""
        from beep.agent.tools.python_intelligence_core import PythonJediAdapter

        key = str(Path(workspace_root).resolve())
        if key not in self._python_jedi_adapters:
            self._python_jedi_adapters[key] = PythonJediAdapter(workspace_root=Path(workspace_root))
        return self._python_jedi_adapters[key]

    def semble_index(self, workspace_root: Path | str) -> Any:
        """Return the singleton :class:`SembleIndexAdapter` for *workspace_root*."""
        from beep.agent.tools.semantic_search import SembleIndexAdapter

        key = str(Path(workspace_root).resolve())
        if key not in self._semble_index_adapters:
            self._semble_index_adapters[key] = SembleIndexAdapter(
                workspace_root=Path(workspace_root)
            )
        return self._semble_index_adapters[key]

    def plugin_registry(self, workspace_root: Path | str) -> Any:
        """Return the singleton :class:`PluginRegistry` for *workspace_root*."""
        from beep.plugins.registry import PluginRegistry

        key = str(Path(workspace_root).resolve())
        if key not in self._plugin_registries:
            self._plugin_registries[key] = PluginRegistry()
        return self._plugin_registries[key]

    @property
    def template_validator(self) -> Any:
        """Return the singleton :class:`ProjectTemplateValidator`."""
        if self._template_validator is None:
            from beep.templates.validator import ProjectTemplateValidator

            self._template_validator = ProjectTemplateValidator(self.template_registry)
        return self._template_validator

    @property
    def rollback(self) -> Any:
        """Return the singleton :class:`RollbackManager`."""
        if self._rollback_manager is None:
            from beep.editing.rollback import RollbackManager

            self._rollback_manager = RollbackManager()
        return self._rollback_manager

    @property
    def standards_reviewer(self) -> Any:
        """Return the singleton :class:`StandardsReviewer`."""
        if self._standards_reviewer is None:
            from beep.standards.review import StandardsReviewer

            self._standards_reviewer = StandardsReviewer()
        return self._standards_reviewer

    # ------------------------------------------------------------------
    # Session manager (requires config, so it is exposed as a factory)
    # ------------------------------------------------------------------
    # Session manager (requires config, so it is exposed as a factory)
    # ------------------------------------------------------------------

    def session_manager(self, config: Any, client: Any | None = None) -> Any:
        """Create a :class:`SessionManager` bound to *config*.

        Session managers are **not** globally singleton because each chat
        session may use a different config or API client.  Callers that need
        a per-session singleton should store the result on the session object
        itself (see :mod:`beep.chat.session_runtime_state`).
        """
        from beep.sessions.manager import SessionManager

        return SessionManager(config=config, client=client)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all cached singleton instances.

        Useful in tests to ensure a fresh registry.
        """
        self._code_analysis = None
        self._bookmarks = None
        self._tasks = None
        self._permissions = None
        self._hooks = None
        self._language_registry = None
        self._template_registry = None
        # Note: API clients hold async httpx clients; we drop the references
        # and let garbage collection / process exit clean them up.
        self._api_clients.clear()
        self._mcp_clients.clear()
        self._smart_contexts.clear()
        self._auto_contexts.clear()
        self._chat_contexts.clear()
        self._tree_sitter_parser = None
        self._python_jedi_adapters.clear()
        self._semble_index_adapters.clear()
        self._plugin_registries.clear()
        self._template_validator = None
        self._rollback_manager = None
        self._standards_reviewer = None
        for watcher in self._watchers.values():
            watcher.stop()
        self._watchers.clear()

    @classmethod
    def reset_registry(cls) -> None:
        """Destroy the global :class:`AppService` instance entirely."""
        if cls._instance is not None:
            cls._instance.reset()
        cls._instance = None
        global _app_service
        _app_service = None


# Global accessor
_app_service: AppService | None = None


def get_app_service() -> AppService:
    """Return the global :class:`AppService` singleton."""
    global _app_service
    if _app_service is None:
        _app_service = AppService()
    return _app_service
