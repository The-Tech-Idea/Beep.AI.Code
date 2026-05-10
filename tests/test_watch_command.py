"""Tests for watch command behavior."""

from __future__ import annotations

from unittest.mock import patch

from beep.commands.watch import watch_cmd


def test_watch_cmd_handles_start_error(capsys) -> None:
    class _FailingWatcherService:
        def __init__(self, *_args, **_kwargs) -> None:
            self.stopped = False

        def add_rule(self, *_args, **_kwargs) -> str:
            return "ok"

        def start(self, *_args, **_kwargs) -> None:
            raise RuntimeError("boom")

        def stop(self) -> None:
            self.stopped = True

    with patch("beep.watcher.service.WatcherService", _FailingWatcherService):
        watch_cmd(pattern="*.py", command="pytest", debounce=1.0, path=".")
    out = capsys.readouterr().out
    assert "watcher error: boom" in out.lower()


def test_watch_cmd_stops_on_keyboard_interrupt(capsys) -> None:
    state = {"stopped": False}

    class _WatcherService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def add_rule(self, *_args, **_kwargs) -> str:
            return "ok"

        def start(self, *_args, **_kwargs) -> None:
            return None

        def stop(self) -> None:
            state["stopped"] = True

    with patch("beep.watcher.service.WatcherService", _WatcherService):
        with patch("beep.commands.watch.time.sleep", side_effect=KeyboardInterrupt):
            watch_cmd(pattern="*.py", command="pytest", debounce=1.0, path=".")
    out = capsys.readouterr().out
    assert "watcher stopped" in out.lower()
    assert state["stopped"] is True


def test_watch_cmd_reports_callback_runtime_error(capsys) -> None:
    class _WatcherService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def add_rule(self, *_args, **_kwargs) -> str:
            return "ok"

        def start(self, callback) -> None:
            class _Rule:
                command = "pytest"

            class _File:
                name = "a.py"

            callback(type("Evt", (), {"file": _File(), "rule": _Rule()})())

        def stop(self) -> None:
            return None

    def _raise_run(coro):
        coro.close()
        raise RuntimeError("loop fail")

    with patch("beep.watcher.service.WatcherService", _WatcherService):
        with patch("beep.commands.watch.asyncio.run", side_effect=_raise_run):
            with patch("beep.commands.watch.time.sleep", side_effect=KeyboardInterrupt):
                watch_cmd(pattern="*.py", command="pytest", debounce=1.0, path=".")
    out = capsys.readouterr().out
    assert "watch callback error: loop fail" in out.lower()
