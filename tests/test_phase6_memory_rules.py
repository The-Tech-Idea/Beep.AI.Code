"""Tests for Phase 6: Memory, Rules, and Skills."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beep.memory.agent import AgentMemory
from beep.memory.loader import ProjectMemory, load_project_memory
from beep.rules.resolver import resolve_rules_for_path, resolve_rules_for_paths


# ---------------------------------------------------------------------------
# TestProjectMemoryPromptSection
# ---------------------------------------------------------------------------
class TestProjectMemoryPromptSection:
    def test_to_prompt_section_exists(self) -> None:
        mem = ProjectMemory(global_instructions="Be concise.")
        assert hasattr(mem, "to_prompt_section")

    def test_to_prompt_section_matches_to_system_prompt(self) -> None:
        mem = ProjectMemory(
            global_instructions="Be concise.",
            habits=["Write tests"],
            commands={"review": "Run a code review"},
        )
        assert mem.to_prompt_section() == mem.to_system_prompt()

    def test_to_prompt_section_empty_when_no_content(self) -> None:
        mem = ProjectMemory()
        assert mem.to_prompt_section() == ""

    def test_to_prompt_section_includes_habits(self) -> None:
        mem = ProjectMemory(habits=["Always lint before commit"])
        section = mem.to_prompt_section()
        assert "Always lint before commit" in section
        assert "Project Habits" in section


# ---------------------------------------------------------------------------
# TestCustomCommandRegistry
# ---------------------------------------------------------------------------
class TestCustomCommandRegistry:
    def test_build_custom_command_registry_empty(self) -> None:
        from beep.chat.command_registry import build_custom_command_registry

        result = build_custom_command_registry({})
        assert result == {}

    def test_build_custom_command_registry_creates_commands(self) -> None:
        from beep.chat.command_registry import build_custom_command_registry

        result = build_custom_command_registry({"review": "Run code review", "test": "Run tests"})
        assert "review" in result
        assert "test" in result
        assert result["review"].name == "review"
        assert result["test"].name == "test"

    def test_custom_command_description_is_message_template(self) -> None:
        from beep.chat.command_registry import build_custom_command_registry

        result = build_custom_command_registry({"review": "Please review this code"})
        assert result["review"].description == "Please review this code"

    def test_custom_commands_merged_in_build_registry(self) -> None:
        """Memory custom commands do not appear in base build_command_registry (no workspace)."""
        from beep.chat.command_registry import build_command_registry

        registry = build_command_registry()
        # Base registry should have standard commands
        assert "help" in registry
        assert "quit" in registry
        assert "memory" in registry  # MemoryReloadCommand


# ---------------------------------------------------------------------------
# TestMemoryReloadCommand
# ---------------------------------------------------------------------------
class TestMemoryReloadCommand:
    @pytest.mark.asyncio
    async def test_reload_clears_cache(self) -> None:
        from beep.chat.commands.memory import MemoryReloadCommand

        cmd = MemoryReloadCommand()
        assert cmd.name == "memory"

        cleared = []
        fake_runtime = SimpleNamespace(
            memory=ProjectMemory(),
            commands={},
            rules=[],
            rule_errors=[],
            skills=[],
            skill_errors=[],
            skill_roots=[],
        )

        session = SimpleNamespace(
            _workspace=Path("/tmp/ws"),
            _plugins_enabled=True,
            _memory=None,
            _rules=[],
            _rule_errors=[],
            _skills=[],
            _skill_errors=[],
            _skill_roots=[],
            _commands={},
            _skill_resolver=None,
        )

        with (
            patch(
                "beep.runtime.workspace.clear_workspace_runtime_cache",
                side_effect=lambda: cleared.append(True),
            ),
            patch(
                "beep.runtime.workspace.get_workspace_runtime",
                return_value=fake_runtime,
            ),
        ):
            await cmd.execute("reload", {"session": session, "client": MagicMock()})

        assert cleared, "clear_workspace_runtime_cache was not called"

    @pytest.mark.asyncio
    async def test_reload_updates_session_memory(self) -> None:
        from beep.chat.commands.memory import MemoryReloadCommand

        cmd = MemoryReloadCommand()
        new_memory = ProjectMemory(global_instructions="Updated instructions.")
        fake_runtime = SimpleNamespace(
            memory=new_memory,
            commands={},
            rules=[],
            rule_errors=[],
            skills=[],
            skill_errors=[],
            skill_roots=[],
        )
        session = SimpleNamespace(
            _workspace=Path("/tmp/ws"),
            _plugins_enabled=True,
            _memory=ProjectMemory(),
            _rules=[],
            _rule_errors=[],
            _skills=[],
            _skill_errors=[],
            _skill_roots=[],
            _commands={},
            _skill_resolver=None,
        )

        with (
            patch("beep.runtime.workspace.clear_workspace_runtime_cache"),
            patch("beep.runtime.workspace.get_workspace_runtime", return_value=fake_runtime),
        ):
            await cmd.execute("reload", {"session": session, "client": MagicMock()})

        assert session._memory is new_memory

    @pytest.mark.asyncio
    async def test_reload_unknown_subcommand_prints_usage(self, capsys) -> None:
        from beep.chat.commands.memory import MemoryReloadCommand

        cmd = MemoryReloadCommand()
        # Should not crash; prints usage
        with patch("beep.runtime.workspace.clear_workspace_runtime_cache"):
            await cmd.execute("unknown", {"session": None, "client": MagicMock()})


# ---------------------------------------------------------------------------
# TestCustomCommandExecute
# ---------------------------------------------------------------------------
class TestCustomCommandExecute:
    @pytest.mark.asyncio
    async def test_custom_command_sends_message(self) -> None:
        from beep.chat.commands.base import CustomCommand

        cmd = CustomCommand("review", "Please review this code")
        messages: list[dict] = [{"role": "system", "content": "sys"}]
        session = SimpleNamespace(
            _messages=messages,
            _session_id="s-1",
        )
        mock_stream = AsyncMock()
        with (
            patch("beep.sessions.history.save_message"),
            patch("beep.chat.commands.llm_turns.stream_assistant_turn", mock_stream),
        ):
            await cmd.execute("", {"session": session, "client": MagicMock()})

        assert any(m["role"] == "user" and "review" in m["content"].lower() for m in messages)
        mock_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_command_appends_args(self) -> None:
        from beep.chat.commands.base import CustomCommand

        cmd = CustomCommand("review", "Please review this code")
        messages: list[dict] = [{"role": "system", "content": "sys"}]
        session = SimpleNamespace(_messages=messages, _session_id="s-1")

        with (
            patch("beep.sessions.history.save_message"),
            patch("beep.chat.commands.llm_turns.stream_assistant_turn", AsyncMock()),
        ):
            await cmd.execute("auth.py", {"session": session, "client": MagicMock()})

        user_msg = next(m for m in messages if m["role"] == "user")
        assert "auth.py" in user_msg["content"]

    @pytest.mark.asyncio
    async def test_custom_command_noop_when_session_none(self) -> None:
        from beep.chat.commands.base import CustomCommand

        cmd = CustomCommand("review", "Please review this code")
        # Should not raise
        await cmd.execute("", {"session": None, "client": MagicMock()})


# ---------------------------------------------------------------------------
# TestIgnoreMatcherBeepDir
# ---------------------------------------------------------------------------
class TestIgnoreMatcherBeepDir:
    def test_beep_dir_ignore_patterns_loaded(self) -> None:
        from beep.workspace.ignore import IgnoreMatcher

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            beep_dir = root / ".beep"
            beep_dir.mkdir()
            (beep_dir / "ignore").write_text("*.log\nsecret/\n", encoding="utf-8")

            matcher = IgnoreMatcher(root)
            assert matcher.is_ignored(root / "app.log")
            assert matcher.is_ignored(root / "secret" / "config.json")

    def test_beep_dir_ignore_combined_with_beepignore(self) -> None:
        from beep.workspace.ignore import IgnoreMatcher

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".beepignore").write_text("*.tmp\n", encoding="utf-8")
            beep_dir = root / ".beep"
            beep_dir.mkdir()
            (beep_dir / "ignore").write_text("*.log\n", encoding="utf-8")

            matcher = IgnoreMatcher(root)
            # Both sources should be active
            assert matcher.is_ignored(root / "file.tmp")
            assert matcher.is_ignored(root / "file.log")


# ---------------------------------------------------------------------------
# TestResolveRulesForPaths
# ---------------------------------------------------------------------------
class TestResolveRulesForPaths:
    def _make_rule(self, applies_to: str | None, name: str = "rule") -> object:
        from beep.rules.loader import LoadedRule

        return LoadedRule(
            source=Path(f"{name}.md"),
            content=f"Content of {name}",
            applies_to=applies_to,
        )

    def test_empty_paths_returns_all_rules(self) -> None:
        r1 = self._make_rule(None, "r1")
        r2 = self._make_rule("src/**", "r2")
        result = resolve_rules_for_paths([r1, r2], [])
        assert r1 in result
        assert r2 in result

    def test_union_of_rules_for_multiple_paths(self) -> None:
        r1 = self._make_rule("src/*.py", "r1")
        r2 = self._make_rule("tests/*.py", "r2")
        r3 = self._make_rule("README.md", "r3")
        result = resolve_rules_for_paths([r1, r2, r3], ["src/main.py", "tests/test_main.py"])
        names = [r.source.name for r in result]
        assert "r1.md" in names
        assert "r2.md" in names
        assert "r3.md" not in names

    def test_no_duplicates_when_rule_matches_multiple_paths(self) -> None:
        r1 = self._make_rule(None, "global")  # matches everything
        result = resolve_rules_for_paths([r1], ["src/a.py", "src/b.py"])
        assert result.count(r1) == 1

    def test_preserves_order(self) -> None:
        r1 = self._make_rule("src/**", "r1")
        r2 = self._make_rule("tests/**", "r2")
        result = resolve_rules_for_paths([r1, r2], ["src/main.py", "tests/test.py"])
        assert result[0] is r1
        assert result[1] is r2


# ---------------------------------------------------------------------------
# TestAgentMemory
# ---------------------------------------------------------------------------
class TestAgentMemory:
    def test_remember_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mem = AgentMemory(Path(td))
            mem.remember("test_runner", "pytest")
            assert mem.get("test_runner") == "pytest"

    def test_forget(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mem = AgentMemory(Path(td))
            mem.remember("key", "val")
            mem.forget("key")
            assert mem.get("key") is None

    def test_clear_removes_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mem = AgentMemory(Path(td))
            mem.remember("key", "val")
            assert (Path(td) / ".beep" / "session_memory.json").exists()
            mem.clear()
            assert not (Path(td) / ".beep" / "session_memory.json").exists()
            assert mem.all_facts() == {}

    def test_to_prompt_section_empty_when_no_facts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mem = AgentMemory(Path(td))
            assert mem.to_prompt_section() == ""

    def test_to_prompt_section_includes_facts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mem = AgentMemory(Path(td))
            mem.remember("entry_point", "src/main.py")
            section = mem.to_prompt_section()
            assert "Session Memory" in section
            assert "entry_point" in section
            assert "src/main.py" in section

    def test_persist_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            mem1 = AgentMemory(path)
            mem1.remember("runner", "pytest")
            mem1.remember("linter", "ruff")

            mem2 = AgentMemory(path)
            mem2.load()
            assert mem2.get("runner") == "pytest"
            assert mem2.get("linter") == "ruff"

            payload = json.loads((path / ".beep" / "session_memory.json").read_text(encoding="utf-8"))
            assert payload["schema_version"] == 1
            assert payload["facts"]["runner"] == "pytest"

    def test_load_migrates_legacy_session_memory_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            beep_dir = path / ".beep"
            beep_dir.mkdir()
            memory_path = beep_dir / "session_memory.json"
            memory_path.write_text(json.dumps({"runner": "pytest"}), encoding="utf-8")

            mem = AgentMemory(path)
            mem.load()

            assert mem.get("runner") == "pytest"
            payload = json.loads(memory_path.read_text(encoding="utf-8"))
            assert payload["schema_version"] == 1
            assert payload["facts"]["runner"] == "pytest"

    def test_load_ignores_unsupported_session_memory_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            beep_dir = path / ".beep"
            beep_dir.mkdir()
            (beep_dir / "session_memory.json").write_text(
                json.dumps({"schema_version": 99, "facts": {"runner": "pytest"}}),
                encoding="utf-8",
            )

            mem = AgentMemory(path)
            mem.load()

            assert mem.all_facts() == {}

    def test_load_tolerates_corrupted_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            beep_dir = path / ".beep"
            beep_dir.mkdir()
            (beep_dir / "session_memory.json").write_text("NOT JSON", encoding="utf-8")
            mem = AgentMemory(path)
            mem.load()  # Should not raise
            assert mem.all_facts() == {}


# ---------------------------------------------------------------------------
# TestSkillInjectionInAgentPrompt
# ---------------------------------------------------------------------------
class TestSkillInjectionInAgentPrompt:
    def test_skill_query_injects_matching_skill(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            # Create a skill file
            skill_dir = path / ".beep" / "skills"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "test_writing.md"
            skill_file.write_text(
                "---\n"
                "name: test_writing\n"
                "description: How to write unit tests\n"
                "triggers: [unit test, pytest, test]\n"
                "priority: 1\n"
                "---\n"
                "Always use pytest. Write descriptive test names.",
                encoding="utf-8",
            )

            from beep.coding.prompt_context import build_workspace_system_prompt

            prompt = build_workspace_system_prompt(
                "assistant", path, skill_query="write a unit test for the login function"
            )
            assert "pytest" in prompt or "test_writing" in prompt

    def test_no_skill_injection_without_query(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            skill_dir = path / ".beep" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "test_writing.md").write_text(
                "---\nname: test_writing\ntriggers: [test]\npriority: 1\n---\nUse pytest.",
                encoding="utf-8",
            )
            from beep.coding.prompt_context import build_workspace_system_prompt

            prompt = build_workspace_system_prompt("assistant", path)
            assert "Active Skills" not in prompt


