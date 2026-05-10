"""Phase 4 tests — context management, prompts, and tool injection."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from beep.chat.prompts import (
    CODE_AGENT,
    build_tool_list_section,
    get_system_prompt,
)
from beep.context.window import ContextBudget, _group_conversation_pairs, truncate_messages


# ---------------------------------------------------------------------------
# Prompt tests
# ---------------------------------------------------------------------------


class TestGetSystemPrompt:
    def test_agent_mode_returns_code_agent(self) -> None:
        prompt = get_system_prompt("agent")
        assert prompt == CODE_AGENT

    def test_agent_prompt_contains_tool_guidance(self) -> None:
        prompt = get_system_prompt("agent")
        assert "file_read" in prompt
        assert "file_edit" in prompt
        assert "shell" in prompt

    def test_agent_prompt_contains_read_before_edit_rule(self) -> None:
        prompt = get_system_prompt("agent")
        assert "read" in prompt.lower()
        assert "edit" in prompt.lower()

    def test_assistant_mode_unchanged(self) -> None:
        prompt = get_system_prompt("assistant")
        assert "Beep.AI.Code" in prompt
        assert prompt != CODE_AGENT

    def test_unknown_mode_falls_back_to_assistant(self) -> None:
        prompt = get_system_prompt("nonexistent_mode")
        assert prompt == get_system_prompt("assistant")


class TestBuildToolListSection:
    def _make_tool(self, name: str, description: str) -> MagicMock:
        t = MagicMock()
        t.name = name
        t.description = description
        return t

    def test_empty_tools_returns_empty_string(self) -> None:
        assert build_tool_list_section([]) == ""

    def test_section_header_present(self) -> None:
        tools = [self._make_tool("file_read", "Read a file from the workspace.")]
        section = build_tool_list_section(tools)
        assert "### Available Tools" in section

    def test_tool_name_appears_in_section(self) -> None:
        tools = [
            self._make_tool("file_read", "Read a file."),
            self._make_tool("shell", "Run shell commands."),
        ]
        section = build_tool_list_section(tools)
        assert "`file_read`" in section
        assert "`shell`" in section

    def test_description_truncated_at_first_sentence(self) -> None:
        tools = [self._make_tool("file_read", "Read a file. Extra detail here.")]
        section = build_tool_list_section(tools)
        assert "Extra detail here" not in section
        assert "Read a file" in section

    def test_tool_without_description_still_listed(self) -> None:
        t = MagicMock()
        t.name = "mystery_tool"
        t.description = None
        section = build_tool_list_section([t])
        assert "`mystery_tool`" in section


# ---------------------------------------------------------------------------
# truncate_messages pair-safety tests
# ---------------------------------------------------------------------------


class TestGroupConversationPairs:
    def test_plain_messages_form_singleton_groups(self) -> None:
        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        groups = _group_conversation_pairs(msgs)
        assert len(groups) == 2
        assert groups[0] == [msgs[0]]
        assert groups[1] == [msgs[1]]

    def test_tool_calls_assistant_and_tool_results_grouped(self) -> None:
        msgs = [
            {"role": "user", "content": "run it"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]},
            {"role": "tool", "tool_call_id": "c1", "content": "result 1"},
            {"role": "tool", "tool_call_id": "c2", "content": "result 2"},
            {"role": "assistant", "content": "done"},
        ]
        groups = _group_conversation_pairs(msgs)
        assert len(groups) == 3
        # First group: user message alone.
        assert groups[0] == [msgs[0]]
        # Second group: assistant+tool_calls + two tool results.
        assert groups[1] == [msgs[1], msgs[2], msgs[3]]
        # Third group: final assistant message alone.
        assert groups[2] == [msgs[4]]

    def test_empty_list_returns_empty_groups(self) -> None:
        assert _group_conversation_pairs([]) == []


class TestTruncateMessages:
    def test_empty_returns_empty(self) -> None:
        assert truncate_messages([], ContextBudget()) == []

    def test_system_message_always_kept(self) -> None:
        msgs = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "hi"},
        ]
        result = truncate_messages(msgs, ContextBudget(max_tokens=10_000))
        assert result[0]["role"] == "system"

    def test_recent_messages_kept_over_old(self) -> None:
        # Tight budget — only newest messages fit.
        # Each message is ~100 chars → ~35 tokens with 0.35 ratio.
        old_msg = {"role": "user", "content": "old " * 200}   # ~800 chars → ~280 tokens
        new_msg = {"role": "user", "content": "new"}           # tiny
        msgs = [old_msg, new_msg]
        budget = ContextBudget(max_tokens=200, reserved_for_response=50)
        result = truncate_messages(msgs, budget)
        contents = [m["content"] for m in result]
        assert "new" in contents
        assert "old " * 200 not in contents

    def test_tool_call_group_kept_together(self) -> None:
        """An assistant+tool_calls block and its tool results must not be split."""
        system = {"role": "system", "content": "sys"}
        user = {"role": "user", "content": "do it"}
        assistant_tc = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "x"}],
        }
        tool_result = {"role": "tool", "tool_call_id": "x", "content": "result"}
        final = {"role": "assistant", "content": "done"}

        msgs = [system, user, assistant_tc, tool_result, final]
        result = truncate_messages(msgs, ContextBudget(max_tokens=50_000))

        # All messages should fit in a large budget.
        assert len(result) == 5

    def test_tool_call_group_dropped_atomically(self) -> None:
        """If budget is very tight the tool_calls+tool group is dropped as a unit."""
        system = {"role": "system", "content": "s"}
        # Large paired group that won't fit.
        big_tc = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "t1"}],
        }
        big_tool = {
            "role": "tool",
            "tool_call_id": "t1",
            "content": "x" * 3000,  # large result
        }
        final = {"role": "assistant", "content": "done"}

        msgs = [system, big_tc, big_tool, final]
        # Budget just big enough for system + final, but not the tool group.
        budget = ContextBudget(max_tokens=200, reserved_for_response=50)
        result = truncate_messages(msgs, budget)

        roles = [m["role"] for m in result]
        # The tool result alone must never appear without the assistant+tool_calls.
        tool_in = any(m.get("role") == "tool" for m in result)
        tc_in = any(m.get("tool_calls") for m in result)
        assert tool_in == tc_in, "tool and tool_calls messages must be kept or dropped together"

    def test_budget_updated(self) -> None:
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
        budget = ContextBudget(max_tokens=10_000)
        truncate_messages(msgs, budget)
        assert budget.system_prompt_tokens > 0
        assert budget.message_tokens >= 0


# ---------------------------------------------------------------------------
# context/builder omit warning test
# ---------------------------------------------------------------------------


class TestBuildContextOmitWarning:
    def test_omit_warning_when_files_exceed_limit(self) -> None:
        from beep.context.builder import MAX_CONTEXT_FILES, build_context

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Create MAX_CONTEXT_FILES + 2 files.
            files = []
            for i in range(MAX_CONTEXT_FILES + 2):
                f = root / f"file_{i:02d}.py"
                f.write_text(f"# file {i}\n", encoding="utf-8")
                files.append(f)

            result = build_context(files, workspace_root=root)
            # The omit notice should mention the extra files.
            assert "omitted" in result
            assert "file_10" in result or "file_11" in result

    def test_no_warning_when_within_limit(self) -> None:
        from beep.context.builder import MAX_CONTEXT_FILES, build_context

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = []
            for i in range(MAX_CONTEXT_FILES - 1):
                f = root / f"file_{i:02d}.py"
                f.write_text(f"# file {i}\n", encoding="utf-8")
                files.append(f)

            result = build_context(files, workspace_root=root)
            assert "omitted" not in result


# ---------------------------------------------------------------------------
# smart.py select_context_files smoke test
# ---------------------------------------------------------------------------


class TestSelectContextFiles:
    def test_returns_list_of_paths(self) -> None:
        from beep.context.smart import select_context_files

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")

            result = select_context_files("main", workspace_root=root)
            assert isinstance(result, list)
            # All returned items must be Path objects pointing to existing files.
            for p in result:
                assert isinstance(p, Path)
                assert p.exists()

    def test_empty_query_returns_list(self) -> None:
        from beep.context.smart import select_context_files

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = select_context_files("", workspace_root=root)
            assert isinstance(result, list)

    def test_max_files_respected(self) -> None:
        from beep.context.smart import select_context_files

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Create more files than the limit.
            for i in range(15):
                (root / f"f{i}.py").write_text("x\n", encoding="utf-8")
            result = select_context_files("f", workspace_root=root, max_files=5)
            assert len(result) <= 5
