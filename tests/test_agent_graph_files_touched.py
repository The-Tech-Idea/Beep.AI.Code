from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock


class _FilesTouchedFakeToolNode:
    def __init__(self, _tools: list[object]) -> None:
        return None


class TestAgentGraphFilesTouched:
    def _make_runner(self, rules=None):
        from beep.agent.graph import AgentGraphRunner
        from beep.permissions.manager import SandboxMode

        return AgentGraphRunner(
            backend=MagicMock(),
            tools=[],
            workspace_root=Path("/tmp/ws"),
            max_steps=5,
            max_tool_calls_per_step=3,
            max_tool_calls_total=10,
            step_timeout=30.0,
            max_repeated_calls=3,
            max_consecutive_failures=2,
            max_tool_output_chars=4000,
            auto_approve=True,
            sandbox_mode=SandboxMode.WORKSPACE_WRITE,
            system_prompt="system prompt",
            workspace_rules=rules or [],
            session_id="thread-test",
            tool_node_cls=_FilesTouchedFakeToolNode,
        )

    def test_files_touched_initially_empty(self) -> None:
        runner = self._make_runner()
        state = runner.build_initial_state("inspect")
        assert state["files_touched"] == []

    def test_update_files_touched_adds_path(self) -> None:
        runner = self._make_runner()
        state = runner.build_initial_state("inspect")
        runner._update_files_touched(state, "src/main.py")
        assert "src/main.py" in state["files_touched"]

    def test_update_files_touched_deduplicates(self) -> None:
        runner = self._make_runner()
        state = runner.build_initial_state("inspect")
        runner._update_files_touched(state, "src/main.py")
        runner._update_files_touched(state, "src/main.py")
        assert len(state["files_touched"]) == 1

    def test_update_files_touched_injects_new_rules(self) -> None:
        from beep.rules.loader import LoadedRule

        rule = LoadedRule(
            source=Path("src_rule.md"),
            content="Always add type hints.",
            applies_to="src/*.py",
        )
        runner = self._make_runner(rules=[rule])
        state = runner.build_initial_state("inspect")
        original_prompt = state["messages"][0]["content"]
        runner._update_files_touched(state, "src/main.py")
        updated_prompt = state["messages"][0]["content"]
        assert "Always add type hints." in updated_prompt
        assert updated_prompt != original_prompt

    def test_update_files_touched_no_duplicate_injection(self) -> None:
        from beep.rules.loader import LoadedRule

        rule = LoadedRule(
            source=Path("src_rule.md"),
            content="Always add type hints.",
            applies_to="src/*.py",
        )
        runner = self._make_runner(rules=[rule])
        state = runner.build_initial_state("inspect")
        runner._update_files_touched(state, "src/main.py")
        runner._update_files_touched(state, "src/other.py")
        updated_prompt = state["messages"][0]["content"]
        assert updated_prompt.count("Always add type hints.") == 1
