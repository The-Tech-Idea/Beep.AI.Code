"""Hook execution lifecycle tests."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from beep.chat.repl import ChatSession
from beep.chat import repl_runtime_support
from beep.config import BeepConfig
from beep.hooks.manager import Hook, HookConfig, load_hooks, run_hooks, save_hooks


def _make_hook_config(*hooks: Hook) -> HookConfig:
    return HookConfig(hooks=list(hooks))


class TestHookManager:
    def test_load_hooks_empty_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            hooks_file = Path(td) / "hooks.json"
            hooks_file.parent.mkdir(parents=True, exist_ok=True)
            hooks_file.write_text("{}", encoding="utf-8")
            with patch("beep.hooks.manager.HOOKS_FILE", hooks_file):
                config = load_hooks()
                assert config.hooks == []

    def test_load_hooks_with_data(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            hooks_file = Path(td) / "hooks.json"
            hooks_file.parent.mkdir(parents=True, exist_ok=True)
            hooks_file.write_text(
                json.dumps(
                    {
                        "hooks": [
                            {"event": "session_start", "command": "echo hello", "enabled": True},
                            {"event": "pre_send", "command": "echo world", "enabled": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch("beep.hooks.manager.HOOKS_FILE", hooks_file):
                config = load_hooks()
                assert len(config.hooks) == 2
                assert config.hooks[0].event == "session_start"
                assert config.hooks[0].enabled is True
                assert config.hooks[1].enabled is False

    def test_load_hooks_missing_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("beep.hooks.manager.HOOKS_FILE", Path("/nonexistent/path/hooks.json"))
        config = load_hooks()
        assert config.hooks == []

    def test_load_hooks_invalid_json(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            hooks_file = Path(td) / "hooks.json"
            hooks_file.parent.mkdir(parents=True, exist_ok=True)
            hooks_file.write_text("not json", encoding="utf-8")
            with patch("beep.hooks.manager.HOOKS_FILE", hooks_file):
                config = load_hooks()
                assert config.hooks == []

    def test_save_and_reload_hooks(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            hooks_file = Path(td) / "hooks.json"
            hooks_file.parent.mkdir(parents=True, exist_ok=True)
            with patch("beep.hooks.manager.HOOKS_FILE", hooks_file):
                config = _make_hook_config(
                    Hook(event="session_start", command="echo start"),
                    Hook(event="session_end", command="echo end"),
                )
                save_hooks(config)
                reloaded = load_hooks()
                assert len(reloaded.hooks) == 2
                assert reloaded.hooks[0].event == "session_start"

    def test_hook_config_add(self) -> None:
        config = HookConfig()
        config.add("pre_send", "echo test")
        assert len(config.hooks) == 1
        assert config.hooks[0].event == "pre_send"

    def test_hook_config_remove(self) -> None:
        config = _make_hook_config(
            Hook(event="pre_send", command="echo a"),
            Hook(event="post_send", command="echo b"),
        )
        assert config.remove(0) is True
        assert len(config.hooks) == 1
        assert config.hooks[0].event == "post_send"
        assert config.remove(99) is False

    def test_hook_config_toggle(self) -> None:
        config = _make_hook_config(Hook(event="pre_send", command="echo test", enabled=True))
        config.toggle(0)
        assert config.hooks[0].enabled is False
        config.toggle(0)
        assert config.hooks[0].enabled is True
        assert config.toggle(99) is False


class TestRunHooks:
    def test_run_hooks_no_matching_event(self) -> None:
        config = _make_hook_config(Hook(event="session_start", command="echo hello"))
        outputs = run_hooks("unknown_event", config)
        assert outputs == []

    def test_run_hooks_disabled_hook(self) -> None:
        config = _make_hook_config(
            Hook(event="pre_send", command="echo should_not_run", enabled=False)
        )
        outputs = run_hooks("pre_send", config)
        assert outputs == []

    def test_run_hooks_captures_stdout(self) -> None:
        config = _make_hook_config(Hook(event="pre_send", command="echo hello"))
        outputs = run_hooks("pre_send", config)
        assert outputs == ["hello"]

    def test_run_hooks_captures_stderr(self) -> None:
        config = _make_hook_config(
            Hook(
                event="pre_send", command="python -c \"import sys; print('err', file=sys.stderr)\""
            )
        )
        outputs = run_hooks("pre_send", config)
        assert any("err" in line for line in outputs)

    def test_run_hooks_timeout(self) -> None:
        config = _make_hook_config(Hook(event="pre_send", command="sleep 60"))
        outputs = run_hooks("pre_send", config)
        assert len(outputs) == 1
        assert "timed out" in outputs[0]

    def test_run_hooks_invalid_command(self) -> None:
        config = _make_hook_config(Hook(event="pre_send", command="nonexistent_command_xyz"))
        outputs = run_hooks("pre_send", config)
        assert len(outputs) == 1
        output_lower = outputs[0].lower()
        assert "error" in output_lower or "not recognized" in output_lower

    def test_run_hooks_multiple_hooks_same_event(self) -> None:
        config = _make_hook_config(
            Hook(event="pre_send", command="echo first"),
            Hook(event="pre_send", command="echo second"),
        )
        outputs = run_hooks("pre_send", config)
        assert outputs == ["first", "second"]


class TestHookExecutionLifecycle:
    @pytest.fixture
    def session(self, monkeypatch: pytest.MonkeyPatch) -> ChatSession:
        with tempfile.TemporaryDirectory() as td:
            monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: Path(td))
            return ChatSession(MagicMock())

    def test_chat_session_has_hook_config(self, session: ChatSession) -> None:
        assert session.hook_config is not None
        assert isinstance(session.hook_config, HookConfig)

    def test_hook_config_cached_on_session(self, session: ChatSession) -> None:
        first = session.hook_config
        second = session.hook_config
        assert first is second

    @pytest.mark.asyncio
    async def test_handle_command_fires_pre_and_post_hooks(
        self,
        session: ChatSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from beep.chat.commands.base import Command

        config = _make_hook_config(
            Hook(event="pre_command", command="echo pre_hook"),
            Hook(event="post_command", command="echo post_hook"),
        )
        monkeypatch.setattr("beep.hooks.manager.HOOKS_FILE", Path("/dev/null"))
        monkeypatch.setattr(session, "_hook_config", config)

        class NoopCommand(Command):
            @property
            def name(self) -> str:
                return "noop"

            @property
            def description(self) -> str:
                return "noop"

            async def execute(self, args: str, ctx: dict) -> None:
                pass

        session._commands["noop"] = NoopCommand()
        console = Console()
        log_mock = MagicMock()

        with patch.object(console, "print") as print_mock:
            await repl_runtime_support.handle_command(
                session, "/noop", console=console, log_event=log_mock
            )

        printed = [
            call.args[0] for call in print_mock.call_args_list if isinstance(call.args[0], str)
        ]
        assert any("pre_hook" in str(p) for p in printed)
        assert any("post_hook" in str(p) for p in printed)

    @pytest.mark.asyncio
    async def test_post_command_hook_fires_on_command_error(
        self,
        session: ChatSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from beep.chat.commands.base import Command

        config = _make_hook_config(
            Hook(event="post_command", command="echo cleanup_hook"),
        )
        monkeypatch.setattr("beep.hooks.manager.HOOKS_FILE", Path("/dev/null"))
        monkeypatch.setattr(session, "_hook_config", config)

        class FailCommand(Command):
            @property
            def name(self) -> str:
                return "fail"

            @property
            def description(self) -> str:
                return "fail"

            async def execute(self, args: str, ctx: dict) -> None:
                raise RuntimeError("fail")

        session._commands["fail"] = FailCommand()
        console = Console()
        log_mock = MagicMock()

        with patch.object(console, "print") as print_mock:
            await repl_runtime_support.handle_command(
                session, "/fail", console=console, log_event=log_mock
            )

        printed = [
            call.args[0] for call in print_mock.call_args_list if isinstance(call.args[0], str)
        ]
        assert any("cleanup_hook" in str(p) for p in printed)

    @pytest.mark.asyncio
    async def test_send_fires_pre_and_post_send_hooks(
        self,
        session: ChatSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = _make_hook_config(
            Hook(event="pre_send", command="echo pre_send_hook"),
            Hook(event="post_send", command="echo post_send_hook"),
        )
        monkeypatch.setattr("beep.hooks.manager.HOOKS_FILE", Path("/dev/null"))
        monkeypatch.setattr(session, "_hook_config", config)

        stream_mock = AsyncMock()
        console = Console()
        log_mock = MagicMock()

        with patch.object(console, "print") as print_mock:
            await repl_runtime_support.send(
                session,
                "hello",
                console=console,
                log_event=log_mock,
                stream_assistant_turn=stream_mock,
                build_rules_context=lambda rules: "",
            )

        printed = [
            call.args[0] for call in print_mock.call_args_list if isinstance(call.args[0], str)
        ]
        assert any("pre_send_hook" in str(p) for p in printed)
        assert any("post_send_hook" in str(p) for p in printed)
