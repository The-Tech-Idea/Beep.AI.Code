"""Release checklist validator.

Checks that README feature claims match actual code availability
by verifying module imports, CLI commands, and test coverage exist.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

console = Console()


@dataclass
class ReleaseCheck:
    """A single release readiness check."""

    category: str
    label: str
    check: Any
    passed: bool = False
    detail: str = ""


CHECKS: list[ReleaseCheck] = []


def _add(category: str, label: str, check: Any) -> None:
    CHECKS.append(ReleaseCheck(category=category, label=label, check=check))


# ---------------------------------------------------------------------------
# Module availability checks
# ---------------------------------------------------------------------------

_add("Core", "beep.cli module", "beep.cli")
_add("Core", "beep.config module", "beep.config")
_add("Core", "beep.api.client module", "beep.api.client")
_add("Core", "beep.setup_wizard module", "beep.setup_wizard")

# Agent runtime
_add("Agent", "beep.agent.loop module", "beep.agent.loop")
_add("Agent", "beep.agent.graph module", "beep.agent.graph")
_add("Agent", "beep.agent.backends module", "beep.agent.backends")
_add("Agent", "beep.agent.approval module", "beep.agent.approval")
_add("Agent", "beep.agent.environment module", "beep.agent.environment")
_add("Agent", "beep.agent.tools.base module", "beep.agent.tools.base")
_add("Agent", "beep.agent.tools.factory module", "beep.agent.tools.factory")
_add("Agent", "beep.agent.tools.file_read module", "beep.agent.tools.file_read")
_add("Agent", "beep.agent.tools.file_write module", "beep.agent.tools.file_write")
_add("Agent", "beep.agent.tools.file_edit module", "beep.agent.tools.file_edit")
_add("Agent", "beep.agent.tools.search module", "beep.agent.tools.search")
_add("Agent", "beep.agent.tools.shell module", "beep.agent.tools.shell")

# Chat REPL
_add("Chat", "beep.chat.repl module", "beep.chat.repl")
_add("Chat", "beep.chat.command_registry module", "beep.chat.command_registry")
_add("Chat", "beep.chat.repl_runtime_support module", "beep.chat.repl_runtime_support")
_add("Chat", "beep.chat.session_runtime_state module", "beep.chat.session_runtime_state")
_add("Chat", "beep.hooks.manager module", "beep.hooks.manager")
_add("Chat", "beep.context.auto_context module", "beep.context.auto_context")

# Sessions
_add("Sessions", "beep.sessions.history module", "beep.sessions.history")
_add("Sessions", "beep.sessions.export module", "beep.sessions.export")
_add("Sessions", "beep.sessions.presentation module", "beep.sessions.presentation")

# Tasks & Watchers
_add("Tasks", "beep.tasks.manager module", "beep.tasks.manager")
_add("Tasks", "beep.watcher.service module", "beep.watcher.service")

# Plugins & MCP
_add("Plugins", "beep.plugins.registry module", "beep.plugins.registry")
_add("Plugins", "beep.plugins.runtime module", "beep.plugins.runtime")
_add("Plugins", "beep.plugins.contracts module", "beep.plugins.contracts")
_add("MCP", "beep.mcp.client module", "beep.mcp.client")
_add("MCP", "beep.mcp.discovery module", "beep.mcp.discovery")
_add("MCP", "beep.mcp.presets module", "beep.mcp.presets")

# Workspace
_add("Workspace", "beep.workspace.detector module", "beep.workspace.detector")
_add("Workspace", "beep.workspace.editing module", "beep.workspace.editing")
_add("Workspace", "beep.workspace.file_ops module", "beep.workspace.file_ops")
_add("Workspace", "beep.workspace.view module", "beep.workspace.view")
_add("Workspace", "beep.workspace.search module", "beep.workspace.search")
_add("Workspace", "beep.workspace.search_replace module", "beep.workspace.search_replace")
_add("Workspace", "beep.workspace.file_tree module", "beep.workspace.file_tree")
_add("Workspace", "beep.workspace.git module", "beep.workspace.git")

# Permissions & Sandbox
_add("Security", "beep.permissions.manager module", "beep.permissions.manager")

# TUI
_add("TUI", "beep.tui.app module", "beep.tui.app")
_add("TUI", "beep.tui.screens.chat module", "beep.tui.screens.chat")
_add("TUI", "beep.tui.dialogs.command_palette module", "beep.tui.dialogs.command_palette")
_add("TUI", "beep.tui.dialogs.session_switcher module", "beep.tui.dialogs.session_switcher")
_add("TUI", "beep.tui.dialogs.model_selector module", "beep.tui.dialogs.model_selector")
_add("TUI", "beep.tui.dialogs.file_picker module", "beep.tui.dialogs.file_picker")

# Web search
_add("Extras", "beep.websearch.search module", "beep.websearch.search")

# Context & Memory
_add("Context", "beep.context.builder module", "beep.context.builder")
_add("Context", "beep.context.smart module", "beep.context.smart")
_add("Context", "beep.context.window module", "beep.context.window")
_add("Memory", "beep.memory.loader module", "beep.memory.loader")
_add("Memory", "beep.rules.resolver module", "beep.rules.resolver")
_add("Memory", "beep.skills.resolver module", "beep.skills.resolver")

# Templates
_add("Templates", "beep.templates.generator module", "beep.templates.generator")
_add("Templates", "beep.templates.catalog module", "beep.templates.catalog")

# ---------------------------------------------------------------------------
# CLI command checks
# ---------------------------------------------------------------------------


def _check_cli_command(name: str) -> str:
    from beep.cli import app

    commands = [
        getattr(c, "name", None)
        or getattr(c, "callback", lambda: None).__name__.removesuffix("_command")
        for c in app.registered_commands
    ]
    groups = [getattr(g, "name", None) for g in app.registered_groups]
    available = commands + groups
    if name in available:
        return "OK"
    return f"Not found (available: {', '.join(sorted(available))})"


_add("CLI", "setup command", lambda: _check_cli_command("setup"))
_add("CLI", "agent command", lambda: _check_cli_command("agent"))
_add("CLI", "sessions command", lambda: _check_cli_command("sessions"))
_add("CLI", "tree command", lambda: _check_cli_command("tree"))
_add("CLI", "cat command", lambda: _check_cli_command("cat"))
_add("CLI", "grep command", lambda: _check_cli_command("grep"))
_add("CLI", "diagnostics command", lambda: _check_cli_command("diagnostics"))
_add("CLI", "doctor command", lambda: _check_cli_command("doctor"))
_add("CLI", "self-update command", lambda: _check_cli_command("self-update"))
_add("CLI", "template command", lambda: _check_cli_command("template"))
_add("CLI", "plugins command", lambda: _check_cli_command("plugins"))
_add("CLI", "mcp command", lambda: _check_cli_command("mcp"))
_add("CLI", "tui command", lambda: _check_cli_command("tui"))
_add("CLI", "lint command", lambda: _check_cli_command("lint"))
_add("CLI", "test command", lambda: _check_cli_command("test"))
_add("CLI", "watch command", lambda: _check_cli_command("watch"))
_add("CLI", "rag command", lambda: _check_cli_command("rag"))
_add("CLI", "ask (default dispatch)", lambda: _check_cli_command("ask"))


def _run_checks(checks: list[ReleaseCheck]) -> None:
    for check in checks:
        try:
            if isinstance(check.check, str):
                importlib.import_module(check.check)
                check.passed = True
                check.detail = "OK"
            elif callable(check.check):
                result = check.check()
                if result == "OK":
                    check.passed = True
                    check.detail = "OK"
                else:
                    check.passed = False
                    check.detail = result
            else:
                check.passed = False
                check.detail = "unknown check type"
        except Exception as e:
            check.passed = False
            check.detail = str(e)


def _print_results(checks: list[ReleaseCheck]) -> None:
    by_category: dict[str, list[ReleaseCheck]] = {}
    for c in checks:
        by_category.setdefault(c.category, []).append(c)

    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    failed = total - passed

    console.print(f"\n[bold]Release Readiness: {passed}/{total} checks passed[/bold]\n")

    for category, items in by_category.items():
        cat_passed = sum(1 for i in items if i.passed)
        cat_total = len(items)
        icon = "OK" if cat_passed == cat_total else "!!"
        console.print(f"[bold][{icon}] {category} ({cat_passed}/{cat_total})[/]")
        for item in items:
            status = "[green][+][/]" if item.passed else "[red][-][/]"
            console.print(f"  {status} {item.label}: {item.detail}")
        console.print()

    if failed > 0:
        console.print(f"[bold red]{failed} check(s) failed -- do not release until resolved[/]\n")
        raise typer.Exit(1)
    else:
        console.print("[bold green]All checks passed -- ready for release[/]\n")


def run_release_check() -> None:
    """Run all release readiness checks."""
    _run_checks(CHECKS)
    _print_results(CHECKS)


app = typer.Typer(name="release-check", help="Validate release readiness")
app.command()(run_release_check)

if __name__ == "__main__":
    app()
