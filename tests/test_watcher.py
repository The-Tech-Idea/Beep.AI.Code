"""Tests for file watcher service."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest
from watchdog.events import FileModifiedEvent

from beep.watcher.service import (
    WatcherService,
    WatchEvent,
    WatchRule,
    WatchRuleHandler,
    execute_watch_event,
)


class TestWatchRule:
    def test_create_rule(self) -> None:
        rule = WatchRule(pattern="*.py", command="pytest", debounce=2.0)
        assert rule.pattern == "*.py"
        assert rule.command == "pytest"
        assert rule.debounce == 2.0
        assert rule.enabled is True


class TestWatcherService:
    def test_add_rule(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            service = WatcherService(root=Path(td))
            result = service.add_rule("*.py", "pytest")
            assert "*.py" in result
            assert len(service.rules) == 1

    def test_remove_rule(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            service = WatcherService(root=Path(td))
            service.add_rule("*.py", "pytest")
            assert service.remove_rule(0) is True
            assert len(service.rules) == 0

    def test_remove_invalid_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            service = WatcherService(root=Path(td))
            assert service.remove_rule(99) is False

    def test_list_rules(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            service = WatcherService(root=Path(td))
            service.add_rule("*.py", "pytest")
            service.add_rule("*.js", "eslint")
            rules = service.list_rules()
            assert len(rules) == 2
            assert rules[0][0] == 0
            assert rules[1][0] == 1

    def test_start_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            service = WatcherService(root=Path(td))
            assert service.is_running is False
            service.start()
            assert service.is_running is True
            service.stop()
            assert service.is_running is False

    def test_double_start(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            service = WatcherService(root=Path(td))
            service.start()
            service.start()
            assert service.is_running is True
            service.stop()


class TestWatchRuleHandler:
    def test_callback_exception_does_not_crash_handler(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file_path = root / "a.py"
            file_path.write_text("print('x')\n", encoding="utf-8")
            rule = WatchRule(pattern="*.py", command="pytest")
            handler = WatchRuleHandler(
                root=root,
                rules=[rule],
                callback=lambda _event: (_ for _ in ()).throw(RuntimeError("boom")),
            )
            event = FileModifiedEvent(str(file_path))
            handler.on_any_event(event)


@pytest.mark.asyncio
async def test_execute_watch_event_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeProcess:
        returncode = 0

        async def communicate(self, *_args, **_kwargs):
            await asyncio.sleep(0.01)
            return b"", b""

        def kill(self) -> None:
            return None

    async def _fake_create(*_args, **_kwargs):
        return _FakeProcess()

    async def _fake_wait_for(coro, *_args, **_kwargs):
        coro.close()
        raise TimeoutError

    monkeypatch.setattr("beep.watcher.service.asyncio.create_subprocess_shell", _fake_create)
    monkeypatch.setattr("beep.watcher.service.asyncio.wait_for", _fake_wait_for)

    rule = WatchRule(pattern="*.py", command="pytest")
    event = WatchEvent(file=Path.cwd() / "x.py", rule=rule, event_type="modified")
    result = await execute_watch_event(event)
    assert "timed out" in result.lower()


@pytest.mark.asyncio
async def test_execute_watch_event_timeout_still_reports_timeout_when_kill_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProcess:
        returncode = 0

        async def communicate(self, *_args, **_kwargs):
            await asyncio.sleep(0.01)
            return b"", b""

        def kill(self) -> None:
            raise RuntimeError("kill failed")

    async def _fake_create(*_args, **_kwargs):
        return _FakeProcess()

    async def _fake_wait_for(coro, *_args, **_kwargs):
        coro.close()
        raise TimeoutError

    monkeypatch.setattr("beep.watcher.service.asyncio.create_subprocess_shell", _fake_create)
    monkeypatch.setattr("beep.watcher.service.asyncio.wait_for", _fake_wait_for)

    rule = WatchRule(pattern="*.py", command="pytest")
    event = WatchEvent(file=Path.cwd() / "x.py", rule=rule, event_type="modified")
    result = await execute_watch_event(event)
    assert "timed out" in result.lower()


@pytest.mark.asyncio
async def test_execute_watch_event_includes_exit_code_when_no_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProcess:
        returncode = 17

        async def communicate(self, *_args, **_kwargs):
            return b"", b""

        def kill(self) -> None:
            return None

    async def _fake_create(*_args, **_kwargs):
        return _FakeProcess()

    monkeypatch.setattr("beep.watcher.service.asyncio.create_subprocess_shell", _fake_create)

    rule = WatchRule(pattern="*.py", command="pytest")
    event = WatchEvent(file=Path.cwd() / "x.py", rule=rule, event_type="modified")
    result = await execute_watch_event(event)
    assert "exited with code 17" in result.lower()
