"""Phase 5 — Chat REPL UX & Slash Commands tests."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.api.streaming import TOOL_CALL_PREFIX, TOOL_CALL_SUFFIX, iter_chat_sse_content
from beep.chat.command_registry import build_command_registry
from beep.chat.commands.base import Command
from beep.chat.commands.code import CatCommand, GrepCommand, TreeCommand
from beep.chat.commands.session import CompactCommand, UndoCommand
from beep.chat.commands.system import (
    ConfigCommand,
    DiagnosticsCommand,
    StatusCommand,
    TemplatesCommand,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(workspace_root: Path, monkeypatch: pytest.MonkeyPatch) -> object:
    """Build a minimal ChatSession without hitting the filesystem."""
    from beep.chat.repl import ChatSession

    monkeypatch.setattr("beep.chat.repl.find_workspace_root", lambda: workspace_root)
    return ChatSession(MagicMock())


# ---------------------------------------------------------------------------
# Alias registration
# ---------------------------------------------------------------------------


class TestAliases:
    def test_aliases_default_empty(self) -> None:
        class _Cmd(Command):
            @property
            def name(self) -> str:
                return "x"

            @property
            def description(self) -> str:
                return "x"

            async def execute(self, args: str, ctx: dict) -> None:
                pass

        assert _Cmd().aliases == []

    def test_clear_alias_c_registered(self) -> None:
        registry = build_command_registry()
        assert "c" in registry
        assert registry["c"].name == "clear"

    def test_alias_resolves_same_command_object(self) -> None:
        registry = build_command_registry()
        assert registry["c"] is registry["clear"]

    def test_all_registry_values_are_commands(self) -> None:
        registry = build_command_registry()
        for key, cmd in registry.items():
            assert isinstance(cmd, Command), f"{key!r} maps to non-Command"


# ---------------------------------------------------------------------------
# CompactCommand local fallback
# ---------------------------------------------------------------------------


class TestCompactFallback:
    @pytest.mark.asyncio
    async def test_keeps_system_plus_five_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        session._messages = [{"role": "system", "content": "sys"}] + [
            {"role": "user", "content": f"u{i}"} for i in range(10)
        ]
        client = AsyncMock()
        # Make server compact endpoint raise so local fallback runs
        client.compact_conversation.side_effect = Exception("no endpoint")
        monkeypatch.setattr("beep.chat.commands.session.replace_session", lambda *a: None)
        await CompactCommand().execute("", {"session": session, "client": client})
        # system + last 5 non-system = 6 total
        assert len(session._messages) == 6
        assert session._messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_skips_when_two_or_fewer_messages(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        session._messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        client = AsyncMock()
        await CompactCommand().execute("", {"session": session, "client": client})
        out = capsys.readouterr().out
        assert "nothing" in out.lower()

    @pytest.mark.asyncio
    async def test_keeps_tail_not_head(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        msgs = [{"role": "system", "content": "sys"}] + [
            {"role": "user", "content": f"msg{i}"} for i in range(8)
        ]
        session._messages = list(msgs)
        client = AsyncMock()
        client.compact_conversation.side_effect = Exception("no endpoint")
        monkeypatch.setattr("beep.chat.commands.session.replace_session", lambda *a: None)
        await CompactCommand().execute("", {"session": session, "client": client})
        # Last 5 messages should be msg3..msg7
        kept_contents = [m["content"] for m in session._messages[1:]]
        assert kept_contents == ["msg3", "msg4", "msg5", "msg6", "msg7"]


# ---------------------------------------------------------------------------
# UndoCommand (conversation history)
# ---------------------------------------------------------------------------


class TestUndoCommand:
    @pytest.mark.asyncio
    async def test_removes_last_user_assistant_pair(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        session._messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "answer"},
        ]
        await UndoCommand().execute("", {"session": session})
        assert len(session._messages) == 1
        assert session._messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_nothing_to_undo_when_only_system(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        session._messages = [{"role": "system", "content": "sys"}]
        await UndoCommand().execute("", {"session": session})
        out = capsys.readouterr().out
        assert "nothing" in out.lower()

    @pytest.mark.asyncio
    async def test_removes_dangling_user_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        session._messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "dangling"},
        ]
        # Simulate a user message with no response yet (shouldn't crash)
        await UndoCommand().execute("", {"session": session})
        assert len(session._messages) == 1

    @pytest.mark.asyncio
    async def test_leaves_earlier_history_intact(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        session._messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "old q"},
            {"role": "assistant", "content": "old a"},
            {"role": "user", "content": "new q"},
            {"role": "assistant", "content": "new a"},
        ]
        await UndoCommand().execute("", {"session": session})
        assert len(session._messages) == 3
        assert session._messages[1]["content"] == "old q"
        assert session._messages[2]["content"] == "old a"


# ---------------------------------------------------------------------------
# StatusCommand — model tiers
# ---------------------------------------------------------------------------


class TestStatusCommand:
    @pytest.mark.asyncio
    async def test_shows_model_tiers_table(self, capsys: pytest.CaptureFixture) -> None:
        client = AsyncMock()
        config_mock = MagicMock()
        config_mock.api_token = None
        client._config = config_mock
        client.health_check.return_value = {
            "status": "ok",
            "coding_model_tiers": {"fast": "gpt-3.5", "smart": "gpt-4"},
        }
        await StatusCommand().execute("", {"client": client})
        out = capsys.readouterr().out
        assert "fast" in out
        assert "gpt-3.5" in out
        assert "smart" in out

    @pytest.mark.asyncio
    async def test_no_tier_table_when_absent(self, capsys: pytest.CaptureFixture) -> None:
        client = AsyncMock()
        config_mock = MagicMock()
        config_mock.api_token = None
        client._config = config_mock
        client.health_check.return_value = {"status": "ok"}
        await StatusCommand().execute("", {"client": client})
        out = capsys.readouterr().out
        assert "Model Tiers" not in out

    @pytest.mark.asyncio
    async def test_coding_model_tiers_excluded_from_main_table(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        client = AsyncMock()
        client.health_check.return_value = {
            "status": "ok",
            "coding_model_tiers": {"fast": "m1"},
        }
        await StatusCommand().execute("", {"client": client})
        out = capsys.readouterr().out
        # The raw key "coding_model_tiers" should NOT appear in the main table
        assert "coding_model_tiers" not in out


class TestTemplatesCommand:
    @pytest.mark.asyncio
    async def test_uses_workspace_root_for_listing(self) -> None:
        workspace_root = Path("workspace-root")

        with patch(
            "beep.chat.commands.system.find_workspace_root",
            return_value=workspace_root,
        ):
            with patch("beep.templates.generator.list_templates", return_value=[]) as list_mock:
                with patch("beep.templates.generator.display_templates") as display_mock:
                    await TemplatesCommand().execute("", {})

        list_mock.assert_called_once_with(None, workspace_root=workspace_root)
        display_mock.assert_called_once_with([])


class TestGrepCommand:
    @pytest.mark.asyncio
    async def test_searches_workspace_with_shared_regex_helper(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sample.py").write_text("target_value\n", encoding="utf-8")

            with patch("beep.chat.commands.code.find_workspace_root", return_value=root):
                await GrepCommand().execute("target_value", {})

        out = capsys.readouterr().out
        assert "sample.py" in out
        assert "target_value" in out


class TestCatCommand:
    @pytest.mark.asyncio
    async def test_uses_shared_workspace_file_helper(self) -> None:
        with patch("beep.chat.commands.code.read_workspace_file", return_value="body") as read_mock:
            await CatCommand().execute("notes.txt", {})

        read_mock.assert_called_once_with("notes.txt", show_numbers=True, highlight=True)


class TestTreeCommand:
    @pytest.mark.asyncio
    async def test_uses_workspace_root_with_shared_tree_helper(self) -> None:
        root = Path("workspace-root")

        with patch("beep.chat.commands.code.find_workspace_root", return_value=root):
            with patch("beep.chat.commands.code.show_workspace_tree") as tree_mock:
                await TreeCommand().execute("", {})

        tree_mock.assert_called_once_with(root)


class TestConfigCommand:
    @pytest.mark.asyncio
    async def test_masks_token_and_shows_config_file(self, capsys: pytest.CaptureFixture) -> None:
        config = MagicMock(
            server_url="http://localhost:8080",
            api_token="secret-token-1234",
            default_model="gpt-test",
        )

        with patch("beep.chat.commands.system.load_config", return_value=config):
            with patch("beep.chat.commands.system.CONFIG_FILE", Path("code.json")):
                await ConfigCommand().execute("", {})

        out = capsys.readouterr().out
        assert "http://localhost:8080" in out
        assert "***1234" in out
        assert "secret-token-1234" not in out
        assert "code.json" in out


class TestDiagnosticsCommand:
    @pytest.mark.asyncio
    async def test_shows_workspace_and_session_counts(self, capsys: pytest.CaptureFixture) -> None:
        session = MagicMock(
            _session_id="session-1",
            _messages=[
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
            _request_count=4,
            _token_count=12345,
        )

        with patch(
            "beep.chat.commands.system.find_workspace_root", return_value=Path("workspace-root")
        ):
            with patch("beep.chat.commands.system.is_git_repo", return_value=True):
                await DiagnosticsCommand().execute("", {"session": session})

        out = capsys.readouterr().out
        assert "workspace-root" in out
        assert "Git: Yes" in out
        assert "Session: session-1" in out
        assert "Messages: 2" in out
        assert "Requests: 4" in out
        assert "12,345" in out


# ---------------------------------------------------------------------------
# AskCommand
# ---------------------------------------------------------------------------


class TestAskCommand:
    @pytest.mark.asyncio
    async def test_ask_does_not_append_to_history(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from beep.chat.commands.llm_turns import AskCommand

        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        original_len = len(session._messages)
        client = AsyncMock()
        client.chat_completion.return_value = {
            "choices": [{"message": {"content": "The answer is 42"}}],
            "usage": {"total_tokens": 5},
        }
        await AskCommand().execute(
            "What is the meaning of life?", {"session": session, "client": client}
        )
        # History must not grow
        assert len(session._messages) == original_len

    @pytest.mark.asyncio
    async def test_ask_prints_usage_when_empty_args(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from beep.chat.commands.llm_turns import AskCommand

        with tempfile.TemporaryDirectory() as td:
            session = _make_session(Path(td), monkeypatch)
        client = AsyncMock()
        await AskCommand().execute("", {"session": session, "client": client})
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "ask" in out.lower()
        client.chat_completion.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ask_is_registered_in_registry(self) -> None:
        registry = build_command_registry()
        assert "ask" in registry


# ---------------------------------------------------------------------------
# run_agent workspace_root parameter
# ---------------------------------------------------------------------------


class TestRunAgentWorkspaceRoot:
    @pytest.mark.asyncio
    async def test_run_agent_uses_provided_workspace_root(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beep.agent import loop as agent_loop

        captured_root: list[Path] = []

        original_gwrt = agent_loop.get_workspace_runtime

        def fake_gwrt(root, **kwargs):
            captured_root.append(root)
            return original_gwrt(root, **kwargs)

        monkeypatch.setattr(agent_loop, "get_workspace_runtime", fake_gwrt)

        env = MagicMock()
        env.is_ready.return_value = True
        env.status.return_value = {"status": "ready", "compatibility_status": "current"}
        env.inject_into_sys_path.return_value = None
        monkeypatch.setattr(agent_loop, "AgentEnvironmentManager", lambda: env)
        monkeypatch.setattr(
            agent_loop,
            "run_graph",
            AsyncMock(
                return_value={
                    "steps_executed": 0,
                    "tool_calls_executed": 0,
                    "run_reason": "test",
                    "final_message": None,
                }
            ),
        )

        client = MagicMock()
        with tempfile.TemporaryDirectory() as td:
            custom_root = Path(td) / "my_workspace"
            custom_root.mkdir()
            await agent_loop.run_agent(client, "do something", workspace_root=custom_root)
        assert custom_root in captured_root

    @pytest.mark.asyncio
    async def test_run_agent_calls_find_workspace_root_when_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beep.agent import loop as agent_loop

        with tempfile.TemporaryDirectory() as td:
            workspace_root = Path(td)

        _orig_gwrt = agent_loop.get_workspace_runtime
        monkeypatch.setattr(
            "beep.agent.loop.get_workspace_runtime",
            lambda root, **kw: _orig_gwrt(workspace_root, **kw),
        )
        fwr_calls: list[int] = []

        def fake_fwr() -> Path:
            fwr_calls.append(1)
            return workspace_root

        env = MagicMock()
        env.is_ready.return_value = True
        env.status.return_value = {"status": "ready", "compatibility_status": "current"}
        env.inject_into_sys_path.return_value = None
        monkeypatch.setattr(agent_loop, "AgentEnvironmentManager", lambda: env)
        monkeypatch.setattr(
            agent_loop,
            "run_graph",
            AsyncMock(
                return_value={
                    "steps_executed": 0,
                    "tool_calls_executed": 0,
                    "run_reason": "test",
                    "final_message": None,
                }
            ),
        )

        with patch("beep.agent.loop.find_workspace_root", fake_fwr):
            await agent_loop.run_agent(client=MagicMock(), goal="test")
        assert fwr_calls, "find_workspace_root should have been called"


# ---------------------------------------------------------------------------
# iter_chat_sse_content tool-call markers
# ---------------------------------------------------------------------------


class TestToolCallMarkers:
    @pytest.mark.asyncio
    async def test_tool_call_name_emits_marker(self) -> None:
        lines = [
            'data: {"choices":[{"delta":{"tool_calls":[{"function":{"name":"bash"}}]}}]}',
            "data: [DONE]",
        ]

        async def _lines():
            for line in lines:
                yield line

        results = []
        async for content, _usage in iter_chat_sse_content(_lines()):
            results.append(content)

        assert any(
            content.startswith(TOOL_CALL_PREFIX) and "bash" in content for content in results
        )

    @pytest.mark.asyncio
    async def test_text_content_unaffected(self) -> None:
        lines = [
            'data: {"choices":[{"delta":{"content":"hello"}}]}',
            "data: [DONE]",
        ]

        async def _lines():
            for line in lines:
                yield line

        results = []
        async for content, _usage in iter_chat_sse_content(_lines()):
            results.append(content)

        assert "hello" in results

    @pytest.mark.asyncio
    async def test_tool_call_marker_stripped_in_render_stream(self) -> None:
        """render_stream should not include the marker text in the returned string."""
        from beep.chat.stream_renderer import render_stream

        marker = f"{TOOL_CALL_PREFIX}my_tool{TOOL_CALL_SUFFIX}"
        text_chunk = "normal text"

        async def _stream():
            yield marker
            yield text_chunk

        result = await render_stream(_stream())
        assert "normal text" in result
        assert TOOL_CALL_PREFIX not in result
        assert TOOL_CALL_SUFFIX not in result

    @pytest.mark.asyncio
    async def test_render_stream_keyboard_interrupt_returns_partial(self) -> None:
        """KeyboardInterrupt during streaming returns partial text with cancellation suffix."""
        from beep.chat.stream_renderer import render_stream

        partial_text = "partial respon"

        async def _interrupted_stream():
            yield partial_text
            raise KeyboardInterrupt

        result = await render_stream(_interrupted_stream())
        assert partial_text in result
        assert "cancelled" in result
