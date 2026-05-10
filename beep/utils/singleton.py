"""Singleton utilities for Beep services and managers.

Provides a consistent pattern for making classes singleton across the codebase.
Two patterns are supported:

1. **Module-level singleton** (no init args): Use a module-level variable and a
   ``get_*()`` function. Simple, no metaclass magic.

2. **Keyed singleton** (init args matter): Override ``__new__`` and store
   instances in a class-level ``_instances`` dict keyed by constructor args.
   This is used when the same class may need different instances for different
   configurations (e.g., different workspace roots).

Examples:
    # Simple singleton (no args)
    _service: CodeAnalysisService | None = None

    def get_code_analysis_service() -> CodeAnalysisService:
        global _service
        if _service is None:
            _service = CodeAnalysisService()
        return _service

    # Keyed singleton (args matter)
    class WatcherService:
        _instances: ClassVar[dict[str, "WatcherService"]] = {}

        def __new__(cls, root: Path) -> "WatcherService":
            key = str(root.resolve())
            instance = cls._instances.get(key)
            if instance is None:
                instance = super().__new__(cls)
                cls._instances[key] = instance
                instance._initialized = False
            return instance

        def __init__(self, root: Path) -> None:
            if getattr(self, "_initialized", False):
                return
            self._initialized = True
            self.root = root
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

T = TypeVar("T")


def singleton_factory(create_fn: Callable[[], T]) -> Callable[[], T]:
    """Wrap a zero-argument factory so it returns the same instance every time.

    Usage::

        def _create_console() -> Console:
            return Console()

        get_console = singleton_factory(_create_console)
    """
    _instance: T | None = None

    def _getter() -> T:
        nonlocal _instance
        if _instance is None:
            _instance = create_fn()
        return _instance

    return _getter


class SingletonMeta(type):
    """Metaclass that makes a class a simple singleton (no keyed instances).

    Usage::

        class MyService(metaclass=SingletonMeta):
            def __init__(self) -> None:
                ...

    Warning:
        This does **not** work well when the constructor takes arguments that
        should produce different instances. Use keyed singleton (``__new__``)
        for that case.
    """

    _instances: dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class KeyedSingletonMeta(type):
    """Metaclass that creates one instance per unique key.

    The first positional argument (or ``key`` keyword argument) is used as the
    cache key. All other args/kwargs are passed through to ``__init__``.

    Usage::

        class WatcherService(metaclass=KeyedSingletonMeta):
            def __init__(self, root: Path) -> None:
                self.root = root

    The instance is cached by ``str(root)`` so ``WatcherService(Path("/a"))``
    and ``WatcherService("/a")`` return the same object.
    """

    _instances: dict[tuple[type, str], Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        key = kwargs.pop("key", None)
        if key is None and args:
            key = str(args[0])
        if key is None:
            raise TypeError(f"{cls.__name__} requires a key (first positional arg or 'key=')")
        cache_key = (cls, key)
        if cache_key not in cls._instances:
            cls._instances[cache_key] = super().__call__(*args, **kwargs)
        return cls._instances[cache_key]


def reset_singleton(cls: type) -> None:
    """Remove the cached singleton instance for a class.

    Useful in tests to ensure a fresh instance.
    """
    if hasattr(cls, "_instances"):
        for k in list(cls._instances.keys()):
            if isinstance(k, tuple) and k[0] is cls:
                del cls._instances[k]
            elif k is cls:
                del cls._instances[k]
