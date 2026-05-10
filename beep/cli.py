"""CLI application for Beep.AI.Code.

Usage:
    beep                    → Interactive chat REPL (like Claude Code)
    beep "question"         → One-shot answer
    beep setup              → Configuration wizard
    beep test               → Run tests
    beep lint --fix         → Lint and fix
    beep --help             → Show all commands
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from beep import __version__
from beep.api.client import BeepAPIClient
from beep.cli_command_registration import (
    known_cli_command_tokens,
    register_core_commands,
    register_subcommand_groups,
    register_top_level_commands,
)
from beep.cli_defaults import parse_default_invocation
from beep import cli_support
from beep.commands.agent import (
    agent_cmd,
    agent_providers_cmd,
    agent_reinstall_cmd,
    agent_resume_cmd,
    agent_setup_cmd,
    agent_status_cmd,
    agent_uninstall_cmd,
)
from beep.commands.agent_bundle import (
    run_agent_export_from_argv,
    run_agent_import_from_argv,
    run_agent_run_from_argv,
)
from beep.commands.agent_deploy import run_agent_deploy_from_argv
from beep.commands.agent_package import run_agent_package_from_argv
from beep.config import CONFIG_FILE, BeepConfig, load_config, save_config
from beep.permissions.manager import SandboxMode
from beep.setup_wizard import ensure_configured, run_agent_provider_setup_wizard, run_setup_wizard

from beep.utils.console import get_console

app = typer.Typer(
    name="beep",
    help="CLI code assistant powered by Beep.AI.Server",
    add_completion=True,
)


def _require_config() -> BeepConfig:
    return ensure_configured()


def _is_subcommand() -> bool:
    """Check if argv contains a known subcommand or flag."""
    args = sys.argv[1:]
    if not args:
        return False
    first = args[0]
    if first.startswith("-"):
        return True
    if first in ("--help", "-h", "--version"):
        return True
    return first in _SUBCOMMANDS


def setup() -> None:
    """Run interactive setup wizard."""
    try:
        run_setup_wizard()
    except KeyboardInterrupt:
        get_console().print("\n[yellow]Setup cancelled[/yellow]")
    except Exception as exc:
        get_console().print(f"[red]Setup failed: {exc}[/red]")
        raise typer.Exit(1)


def status() -> None:
    """Check server health and connection status."""
    config = _require_config()
    cli_support.render_status(
        config=config,
        config_file=CONFIG_FILE,
        console=get_console(),
        client_factory=BeepAPIClient,
    )


def version() -> None:
    """Show version information."""
    get_console().print(f"Beep.AI.Code v{__version__}")


def config_show() -> None:
    """Show current configuration."""
    cli_support.render_config(config=load_config(), config_file=CONFIG_FILE, console=get_console())


def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    cli_support.set_config_value(
        key=key,
        value=value,
        load_config=load_config,
        save_config=save_config,
        console=get_console(),
    )


def chat(
    model: str | None = typer.Option(None, "--model", "-m"),
    mode: str = typer.Option("assistant", "--mode"),
    resume: str | None = typer.Option(None, "--resume", "-r"),
    tokens: bool = typer.Option(False, "--tokens"),
    no_plugins: bool = typer.Option(False, "--no-plugins"),
) -> None:
    """Start interactive chat (same as running `beep` with no args)."""
    from beep.commands.chat import chat_cmd

    chat_cmd(model=model, mode=mode, show_tokens=tokens, resume=resume, no_plugins=no_plugins)


def ask(
    question: str = typer.Argument(...),
    model: str | None = typer.Option(None, "--model", "-m"),
    mode: str = typer.Option("assistant", "--mode"),
) -> None:
    """Ask a one-shot question (same as `beep "question"`)."""
    from beep.commands.ask import ask_cmd

    ask_cmd(question, model=model, mode=mode)


def agent(
    ctx: typer.Context,
    max_steps: int = typer.Option(20, "--max-steps", "-n"),
    yes: bool = typer.Option(False, "--yes", "-y"),
    sandbox: SandboxMode = typer.Option(
        SandboxMode.WORKSPACE_WRITE,
        "--sandbox",
        help="Sandbox mode: read-only, workspace-write, or full-trust.",
    ),
    model: str | None = typer.Option(None, "--model", "-m"),
    no_plugins: bool = typer.Option(False, "--no-plugins"),
    response_json: bool = typer.Option(False, "--response-json"),
    response_schema: Path | None = typer.Option(None, "--response-schema"),
    input_file: list[Path] | None = typer.Option(None, "--input-file"),
    input_image: list[Path] | None = typer.Option(None, "--input-image"),
) -> None:
    """Run autonomous agent or manage the managed agent runtime.

    Special forms:
    - beep agent setup
    - beep agent status
    - beep agent providers
    - beep agent configure [provider_key]
    - beep agent export <agent_id>
    - beep agent import <bundle_file>
    - beep agent deploy <bundle_file_or_id>
    - beep agent package <bundle_file_or_id>
    - beep agent run <bundle_file_or_id> <goal>
    - beep agent resume <thread_id>
    - beep agent reinstall <package|runtime>
    - beep agent uninstall [--yes]
    """
    cli_support.run_agent_dispatch(
        args=list(ctx.args),
        max_steps=max_steps,
        yes=yes,
        sandbox=sandbox,
        model=model,
        no_plugins=no_plugins,
        response_json=response_json,
        response_schema=response_schema,
        input_file=input_file,
        input_image=input_image,
        console=get_console(),
        agent_setup_cmd=agent_setup_cmd,
        agent_status_cmd=agent_status_cmd,
        agent_providers_cmd=agent_providers_cmd,
        run_agent_provider_setup_wizard=run_agent_provider_setup_wizard,
        agent_resume_cmd=agent_resume_cmd,
        agent_reinstall_cmd=agent_reinstall_cmd,
        agent_uninstall_cmd=agent_uninstall_cmd,
        run_agent_export_from_argv=run_agent_export_from_argv,
        run_agent_import_from_argv=run_agent_import_from_argv,
        run_agent_deploy_from_argv=run_agent_deploy_from_argv,
        run_agent_package_from_argv=run_agent_package_from_argv,
        run_agent_run_from_argv=run_agent_run_from_argv,
        agent_cmd=agent_cmd,
    )


def _run_default() -> None:
    """Handle default behavior: beep or beep "question"."""
    args = sys.argv[1:]
    invocation = parse_default_invocation(args, _SUBCOMMANDS)
    if invocation.kind == "ask" and invocation.question:
        from beep.commands.ask import ask_cmd

        ask_cmd(invocation.question, model=invocation.model, mode=invocation.mode)
        return

    from beep.commands.chat import chat_cmd

    chat_cmd(
        model=invocation.model,
        mode=invocation.mode,
        show_tokens=invocation.tokens,
        resume=invocation.resume,
        no_plugins=invocation.no_plugins,
    )


register_core_commands(
    app,
    setup_command=setup,
    status_command=status,
    version_command=version,
    config_show_command=config_show,
    config_set_command=config_set,
    chat_command=chat,
    ask_command=ask,
    agent_command=agent,
)
register_top_level_commands(app)
register_subcommand_groups(app)

_SUBCOMMANDS = known_cli_command_tokens(app)


def main() -> None:
    """Entry point."""
    if _is_subcommand():
        app()
    else:
        _run_default()


if __name__ == "__main__":
    main()
