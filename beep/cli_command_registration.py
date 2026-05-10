"""Top-level Typer command registration helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module

import typer

from beep.commands.rag import rag_collections_cmd, rag_query_cmd
from beep.commands.mcp import mcp_init_cmd, mcp_list_cmd, mcp_presets_cmd, mcp_verify_tools_cmd
from beep.commands.plugins import plugins_add_path_cmd, plugins_paths_cmd
from beep.commands.sessions import sessions_delete_cmd, sessions_export_cmd, sessions_list_cmd
from beep.commands.template import template_cmd, template_list_cmd


@dataclass(frozen=True)
class TopLevelCommandRegistration:
    name: str
    callback: object


@dataclass(frozen=True)
class CoreCommandRegistration:
    callback: object
    name: str | None = None
    command_kwargs: dict[str, object] | None = None


@dataclass(frozen=True)
class CommandGroupRegistration:
    name: str
    help_text: str
    commands: tuple[tuple[str, object], ...]


SPECIAL_COMMAND_TOKENS = (
    "--help",
    "-h",
    "--version",
)


def known_cli_command_tokens(app: typer.Typer, extra_tokens: Iterable[str] = ()) -> frozenset[str]:
    """Return the canonical set of tokens that should be treated as subcommands or CLI flags."""
    command_tokens = tuple(
        filter(None, (_resolve_command_token(command_info) for command_info in app.registered_commands))
    )
    group_tokens = tuple(
        filter(None, (getattr(group_info, "name", None) for group_info in app.registered_groups))
    )
    return frozenset(
        (
            *command_tokens,
            *group_tokens,
            *SPECIAL_COMMAND_TOKENS,
            *tuple(extra_tokens),
        )
    )


def _resolve_command_token(command_info: object) -> str | None:
    explicit_name = getattr(command_info, "name", None)
    if explicit_name:
        return str(explicit_name)
    callback = getattr(command_info, "callback", None)
    callback_name = getattr(callback, "__name__", None)
    if not callback_name:
        return None
    return str(callback_name).removesuffix("_command")


def _invoke_lazy_command(
    module_path: str,
    function_name: str,
    *args: object,
    **kwargs: object,
) -> None:
    callback = getattr(import_module(module_path), function_name)
    callback(*args, **kwargs)


def tui_command(
    model: str | None = typer.Option(None, "--model", "-m"),
    mode: str = typer.Option("assistant", "--mode"),
) -> None:
    """Launch full TUI interface."""
    _invoke_lazy_command("beep.commands.tui", "tui_cmd", model=model, mode=mode)


def tree_command(
    path: str = typer.Argument("."),
    depth: int = typer.Option(3, "--depth", "-d"),
    all_files: bool = typer.Option(False, "--all", "-a"),
) -> None:
    """Display workspace file tree."""
    _invoke_lazy_command("beep.commands.workspace", "tree_cmd", path, depth, all_files)


def cat_command(
    path: str = typer.Argument(...),
    start: int = typer.Option(None, "--start", "-s"),
    end: int = typer.Option(None, "--end", "-e"),
    no_numbers: bool = typer.Option(False, "--no-numbers"),
    no_highlight: bool = typer.Option(False, "--raw"),
) -> None:
    """Display file content with syntax highlighting."""
    _invoke_lazy_command(
        "beep.commands.workspace",
        "cat_cmd",
        path,
        start,
        end,
        no_numbers,
        no_highlight,
    )


def grep_command(
    pattern: str = typer.Argument(...),
    path: str = typer.Argument("."),
    case_sensitive: bool = typer.Option(False, "-C", "--case-sensitive"),
    file_pattern: str = typer.Option(None, "-n", "--name"),
) -> None:
    """Search files for a pattern."""
    _invoke_lazy_command(
        "beep.commands.workspace",
        "grep_cmd",
        pattern,
        path,
        case_sensitive,
        file_pattern,
    )


def edit_command(
    path: str = typer.Argument(...),
    content: str = typer.Option(None, "--content", "-c"),
    no_confirm: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Edit a file with diff preview."""
    _invoke_lazy_command("beep.commands.edit", "edit_cmd", path, content, no_confirm)


def review_command(
    staged: bool = typer.Option(True, "--staged", "-s"),
    file: str | None = typer.Option(None, "--file", "-f"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
    """Review code changes using AI."""
    _invoke_lazy_command("beep.commands.review", "review_cmd", staged, file, model)


def test_command(
    file: str | None = typer.Option(None, "--file", "-f"),
    watch: bool = typer.Option(False, "--watch", "-w"),
    framework: str | None = typer.Option(None, "--framework"),
    timeout: int = typer.Option(120, "--timeout", "-t"),
) -> None:
    """Run tests."""
    _invoke_lazy_command("beep.commands.test", "test_cmd", file, watch, framework, timeout)


def lint_command(
    file: str | None = typer.Option(None, "--file", "-f"),
    fix: bool = typer.Option(False, "--fix"),
    linter: str | None = typer.Option(None, "--linter"),
) -> None:
    """Run linter and optionally fix issues."""
    _invoke_lazy_command("beep.commands.lint", "lint_cmd", file, fix, linter)


def analyze_command(
    path: str = typer.Argument("."),
) -> None:
    """Analyze codebase statistics."""
    _invoke_lazy_command("beep.commands.analyze", "analyze_cmd", path)


def diagnostics_command() -> None:
    """Show diagnostics and system info."""
    _invoke_lazy_command("beep.commands.diagnostics", "diagnostics_cmd")


def doctor_command(
    fix: bool = typer.Option(False, "--fix", help="Apply supported automatic repairs"),
) -> None:
    """Show upgrade and repair guidance for the local CLI environment."""
    _invoke_lazy_command("beep.commands.diagnostics", "doctor_cmd", fix=fix)


def self_update_command(
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Print or execute the detected update workflow for this installation."""
    _invoke_lazy_command("beep.commands.self_update", "self_update_cmd", yes=yes)


def watch_command(
    pattern: str = typer.Option("*.py", "--pattern", "-p"),
    command: str = typer.Option(..., "--command", "-c"),
    debounce: float = typer.Option(1.0, "--debounce", "-d"),
    path: str = typer.Option(".", "--path"),
) -> None:
    """Watch files and run a command on changes."""
    _invoke_lazy_command(
        "beep.commands.watch",
        "watch_cmd",
        pattern=pattern,
        command=command,
        debounce=debounce,
        path=path,
    )


TOP_LEVEL_COMMAND_REGISTRATIONS = (
    TopLevelCommandRegistration("tui", tui_command),
    TopLevelCommandRegistration("tree", tree_command),
    TopLevelCommandRegistration("cat", cat_command),
    TopLevelCommandRegistration("grep", grep_command),
    TopLevelCommandRegistration("edit", edit_command),
    TopLevelCommandRegistration("review", review_command),
    TopLevelCommandRegistration("test", test_command),
    TopLevelCommandRegistration("lint", lint_command),
    TopLevelCommandRegistration("analyze", analyze_command),
    TopLevelCommandRegistration("diagnostics", diagnostics_command),
    TopLevelCommandRegistration("doctor", doctor_command),
    TopLevelCommandRegistration("self-update", self_update_command),
    TopLevelCommandRegistration("watch", watch_command),
)

GROUP_COMMAND_REGISTRATIONS = (
    CommandGroupRegistration(
        name="template",
        help_text="Code generation templates",
        commands=(("generate", template_cmd), ("list", template_list_cmd)),
    ),
    CommandGroupRegistration(
        name="sessions",
        help_text="Session management",
        commands=(("list", sessions_list_cmd), ("export", sessions_export_cmd), ("delete", sessions_delete_cmd)),
    ),
    CommandGroupRegistration(
        name="rag",
        help_text="RAG and semantic search",
        commands=(("query", rag_query_cmd), ("collections", rag_collections_cmd)),
    ),
    CommandGroupRegistration(
        name="plugins",
        help_text="Plugin discovery configuration",
        commands=(("paths", plugins_paths_cmd), ("add-path", plugins_add_path_cmd)),
    ),
    CommandGroupRegistration(
        name="mcp",
        help_text="MCP server discovery and managed definitions",
        commands=(
            ("list", mcp_list_cmd),
            ("presets", mcp_presets_cmd),
            ("init", mcp_init_cmd),
            ("verify-tools", mcp_verify_tools_cmd),
        ),
    ),
)

REGISTERED_TOP_LEVEL_COMMAND_NAMES = tuple(
    registration.name for registration in TOP_LEVEL_COMMAND_REGISTRATIONS
)

REGISTERED_GROUP_COMMAND_NAMES = tuple(
    registration.name for registration in GROUP_COMMAND_REGISTRATIONS
)


def register_core_commands(
    app: typer.Typer,
    *,
    setup_command: object,
    status_command: object,
    version_command: object,
    config_show_command: object,
    config_set_command: object,
    chat_command: object,
    ask_command: object,
    agent_command: object,
) -> None:
    registrations = (
        CoreCommandRegistration(setup_command),
        CoreCommandRegistration(status_command),
        CoreCommandRegistration(version_command),
        CoreCommandRegistration(config_show_command, name="config"),
        CoreCommandRegistration(config_set_command, name="config-set"),
        CoreCommandRegistration(chat_command),
        CoreCommandRegistration(ask_command),
        CoreCommandRegistration(
            agent_command,
            command_kwargs={"context_settings": {"allow_extra_args": True, "ignore_unknown_options": True}},
        ),
    )
    for registration in registrations:
        _register_command(
            app,
            callback=registration.callback,
            name=registration.name,
            command_kwargs=registration.command_kwargs,
        )


def register_top_level_commands(app: typer.Typer) -> None:
    for registration in TOP_LEVEL_COMMAND_REGISTRATIONS:
        _register_command(app, callback=registration.callback, name=registration.name)


def register_subcommand_groups(app: typer.Typer) -> None:
    for registration in GROUP_COMMAND_REGISTRATIONS:
        group_app = typer.Typer(help=registration.help_text)
        for command_name, callback in registration.commands:
            group_app.command(name=command_name)(callback)
        app.add_typer(group_app, name=registration.name)


def _register_command(
    app: typer.Typer,
    *,
    callback: object,
    name: str | None = None,
    command_kwargs: dict[str, object] | None = None,
) -> None:
    kwargs = dict(command_kwargs or {})
    if name is None:
        app.command(**kwargs)(callback)
        return
    app.command(name=name, **kwargs)(callback)