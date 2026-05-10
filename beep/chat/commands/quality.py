"""Quality commands: /review, /test, /lint, /analyze."""

from __future__ import annotations

from typing import Any


from beep.chat.commands._budget import ensure_budget_available
from beep.chat.commands.base import Command
from beep.chat.commands.llm_turns import stream_assistant_turn
from beep.workspace.detector import find_workspace_root
from beep.workspace.git import get_git_diff



from beep.utils.console import get_console
class ReviewCommand(Command):
    @property
    def name(self) -> str:
        return "review"

    @property
    def description(self) -> str:
        return "AI review of git changes"

    @property
    def category(self) -> str:
        return "Quality"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        root = find_workspace_root()
        diff = get_git_diff(root)
        if not diff:
            get_console().print("[yellow]No changes to review[/yellow]")
            return

        session = ctx["session"]
        if not ensure_budget_available(session, command="review"):
            return
        client = ctx["client"]
        session._messages.append(
            {
                "role": "user",
                "content": f"Review these git changes:\n\n```diff\n{diff}\n```",
            }
        )
        session._save("user", "[reviewing git changes]")
        await stream_assistant_turn(
            session=session,
            client=client,
            event="review",
            title="Review",
            empty_message="[yellow]Model returned an empty review[/yellow]",
            empty_error="empty_review",
        )


class TestCommand(Command):
    @property
    def name(self) -> str:
        return "test"

    @property
    def description(self) -> str:
        return "Run tests"

    @property
    def category(self) -> str:
        return "Quality"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        from beep.testrunner.runner import (
            detect_framework,
            display_test_result,
            run_tests,
        )

        root = find_workspace_root()
        fw = detect_framework(root)
        get_console().print(f"[dim]Framework: {fw.value}[/dim]")
        result = await run_tests(root, fw, args or None)
        display_test_result(result)


class LintCommand(Command):
    @property
    def name(self) -> str:
        return "lint"

    @property
    def description(self) -> str:
        return "Run linter"

    @property
    def category(self) -> str:
        return "Quality"

    async def execute(self, args: str, _ctx: dict[str, Any]) -> None:
        from beep.linter.runner import display_lint_result, run_lint

        root = find_workspace_root()
        fix = "--fix" in args
        result = await run_lint(root, file_path=None, fix=fix)
        display_lint_result(result)


class AnalyzeCommand(Command):
    @property
    def name(self) -> str:
        return "analyze"

    @property
    def description(self) -> str:
        return "Codebase statistics"

    @property
    def category(self) -> str:
        return "Quality"

    async def execute(self, _args: str, _ctx: dict[str, Any]) -> None:
        from beep.analysis.stats import analyze_project, display_project_stats

        root = find_workspace_root()
        stats = analyze_project(root)
        display_project_stats(stats)
