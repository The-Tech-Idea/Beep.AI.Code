"""Integration tests that /task, /watch, and session flows survive multiple commands."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from beep.chat.repl import ChatSession


@pytest.mark.asyncio
async def test_task_flow_survives_multiple_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instances: list[object] = []

    class _TaskManager:
        def __init__(self) -> None:
            self.tasks: list[object] = []
            instances.append(self)

        async def start(self, name: str, command: str, cwd: str | None = None) -> object:
            task = SimpleNamespace(
                id=f"task-{len(self.tasks) + 1}",
                name=name,
                command=command,
                status=SimpleNamespace(value="running"),
                output="",
                error="",
            )
            self.tasks.append(task)
            return task

        def get(self, task_id: str) -> object | None:
            for task in self.tasks:
                if task.id == task_id:
                    return task
            return None

        def list_all(self) -> list[object]:
            return list(self.tasks)

        async def cancel(self, task_id: str) -> bool:
            for task in self.tasks:
                if task.id == task_id:
                    task.status = SimpleNamespace(value="cancelled")
                    return True
            return False

        def cancel_all(self) -> None:
            for task in self.tasks:
                task.status = SimpleNamespace(value="cancelled")

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        monkeypatch.setattr("beep.tasks.manager.TaskManager", _TaskManager)
        session = ChatSession(MagicMock())

    await session._handle_command("/task run build pytest")
    assert len(instances) == 1

    await session._handle_command("/task")
    out = capsys.readouterr().out
    assert "build" in out

    await session._handle_command("/task status task-1")
    out = capsys.readouterr().out
    assert "running" in out

    await session._handle_command("/task cancel task-1")
    task = instances[0].get("task-1")
    assert task is not None
    assert task.status.value == "cancelled"

    await session._handle_command("/task")
    out = capsys.readouterr().out
    assert "cancelled" in out
    assert session._task_manager is instances[0]


@pytest.mark.asyncio
async def test_multiple_task_starts_share_same_manager(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instances: list[object] = []

    class _TaskManager:
        def __init__(self) -> None:
            self.tasks: list[object] = []
            instances.append(self)

        async def start(self, name: str, command: str, cwd: str | None = None) -> object:
            task = SimpleNamespace(
                id=f"task-{len(self.tasks) + 1}",
                name=name,
                command=command,
                status=SimpleNamespace(value="running"),
                output="",
                error="",
            )
            self.tasks.append(task)
            return task

        def get(self, task_id: str) -> object | None:
            return next((t for t in self.tasks if t.id == task_id), None)

        def list_all(self) -> list[object]:
            return list(self.tasks)

        async def cancel(self, task_id: str) -> bool:
            return self.get(task_id) is not None

        def cancel_all(self) -> None:
            pass

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        monkeypatch.setattr("beep.tasks.manager.TaskManager", _TaskManager)
        session = ChatSession(MagicMock())

    await session._handle_command("/task run lint ruff")
    await session._handle_command("/task run tests pytest")
    await session._handle_command("/task run format black")

    assert len(instances) == 1
    assert len(instances[0].tasks) == 3

    await session._handle_command("/task")
    out = capsys.readouterr().out
    assert "lint" in out
    assert "tests" in out
    assert "format" in out


@pytest.mark.asyncio
async def test_watch_flow_survives_multiple_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instances: list[object] = []

    class _WatcherService:
        def __init__(self, *_args, **_kwargs) -> None:
            self.rules: list[object] = []
            self._running = False
            instances.append(self)

        def add_rule(self, pattern: str, command: str, debounce: float = 1.0) -> str:
            rule = SimpleNamespace(
                pattern=pattern, command=command, enabled=True, id=f"rule-{len(self.rules) + 1}"
            )
            self.rules.append(rule)
            return f"{pattern} -> {command}"

        def remove_rule(self, index: int) -> bool:
            if 0 <= index < len(self.rules):
                self.rules.pop(index)
                return True
            return False

        def list_rules(self) -> list[tuple[int, object]]:
            return list(enumerate(self.rules))

        def start(self, callback) -> None:
            self._running = True

        def stop(self) -> None:
            self._running = False

        @property
        def is_running(self) -> bool:
            return self._running

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        monkeypatch.setattr("beep.watcher.service.WatcherService", _WatcherService)
        session = ChatSession(MagicMock())

    await session._handle_command("/watch add *.py pytest")
    assert len(instances) == 1

    await session._handle_command("/watch add src/*.js eslint")
    await session._handle_command("/watch add *.md mypy")

    assert len(instances) == 1
    assert len(instances[0].rules) == 3

    await session._handle_command("/watch")
    out = capsys.readouterr().out
    assert "*.py" in out
    assert "*.js" in out
    assert "*.md" in out

    await session._handle_command("/watch remove 0")
    await session._handle_command("/watch")
    out = capsys.readouterr().out
    assert "*.py" not in out
    assert session._watcher is instances[0]


@pytest.mark.asyncio
async def test_clear_nullifies_task_and_watcher_then_new_commands_create_fresh(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    task_instances: list[object] = []
    watcher_instances: list[object] = []

    class _TaskManager:
        def __init__(self) -> None:
            self.tasks: list[object] = []
            task_instances.append(self)

        async def start(self, name: str, command: str, cwd: str | None = None) -> object:
            task = SimpleNamespace(
                id="t-1",
                name=name,
                command=command,
                status=SimpleNamespace(value="running"),
                output="",
                error="",
            )
            self.tasks.append(task)
            return task

        def get(self, task_id: str) -> object | None:
            return next((t for t in self.tasks if t.id == task_id), None)

        def list_all(self) -> list[object]:
            return list(self.tasks)

        async def cancel(self, task_id: str) -> bool:
            return self.get(task_id) is not None

        def cancel_all(self) -> None:
            pass

    class _WatcherService:
        def __init__(self, *_args, **_kwargs) -> None:
            self.rules: list[object] = []
            self._running = False
            watcher_instances.append(self)

        def add_rule(self, pattern: str, command: str, debounce: float = 1.0) -> str:
            self.rules.append(
                SimpleNamespace(pattern=pattern, command=command, enabled=True, id="r-1")
            )
            return "ok"

        def remove_rule(self, index: int) -> bool:
            return False

        def list_rules(self) -> list[tuple[int, object]]:
            return list(enumerate(self.rules))

        def start(self, callback) -> None:
            self._running = True

        def stop(self) -> None:
            self._running = False

        @property
        def is_running(self) -> bool:
            return self._running

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        monkeypatch.setattr("beep.tasks.manager.TaskManager", _TaskManager)
        monkeypatch.setattr("beep.watcher.service.WatcherService", _WatcherService)
        session = ChatSession(MagicMock())

    await session._handle_command("/task run build pytest")
    await session._handle_command("/watch add *.py mypy")

    first_task_mgr = session._task_manager
    first_watcher = session._watcher
    assert first_task_mgr is not None
    assert first_watcher is not None

    await session._handle_command("/clear")

    assert session._task_manager is None
    assert session._watcher is None

    await session._handle_command("/task run rebuild pytest")
    await session._handle_command("/watch add *.js eslint")

    assert len(task_instances) == 2
    assert len(watcher_instances) == 2
    assert session._task_manager is not first_task_mgr
    assert session._watcher is not first_watcher


@pytest.mark.asyncio
async def test_session_undo_survives_multiple_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
        session = ChatSession(MagicMock())

    messages_before = list(session._messages)

    await session._handle_command("/session")
    out = capsys.readouterr().out
    assert session._session_id in out

    session._messages.append({"role": "user", "content": "hello"})
    session._messages.append({"role": "assistant", "content": "hi there"})

    assert len(session._messages) == len(messages_before) + 2

    await session._handle_command("/undo")
    assert len(session._messages) == len(messages_before)

    await session._handle_command("/session")
    out = capsys.readouterr().out
    assert session._session_id in out
