"""Implementation helpers for the Beep CLI entry module."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable

import typer

from beep.agent.provider_options import normalize_reasoning_effort
from beep.system_support import (
    build_cli_config_rows,
    render_health_status,
    render_key_value_table,
)

if TYPE_CHECKING:
    from rich.console import Console


def render_status(
    *,
    config: Any,
    config_file: Any,
    console: Console,
    client_factory: Callable[[Any], Any],
) -> None:
    with console.status("Connecting to server..."):
        client = client_factory(config)
        try:
            health = asyncio.run(client.health_check())
        except Exception as exc:
            console.print(f"[red]Connection failed: {exc}[/red]")
            raise typer.Exit(1)
        finally:
            try:
                asyncio.run(client.close())
            except Exception:
                pass
    render_health_status(
        health=health,
        console=console,
        title="Beep.AI.Server Status",
        prefix_rows=[
            ("Server URL", str(config.server_url)),
            ("Configured", "Yes"),
            ("Config File", str(config_file)),
        ],
        show_model_tiers=False,
    )


def render_config(*, config: Any, config_file: Any, console: Console) -> None:
    render_key_value_table(
        title="Current Configuration",
        key_header="Setting",
        value_header="Value",
        rows=build_cli_config_rows(config=config, config_file=config_file),
        console=console,
    )


def set_config_value(
    *,
    key: str,
    value: str,
    load_config: Callable[[], Any],
    save_config: Callable[[Any], None],
    console: Console,
) -> None:
    config = load_config()

    valid_keys = {
        "server_url",
        "api_token",
        "default_model",
        "agent_backend",
        "agent_base_url",
        "agent_api_key",
        "agent_model",
        "agent_reasoning_effort",
        "agent_parallel_tool_calls",
        "agent_thinking_budget_tokens",
        "max_tokens",
        "temperature",
    }
    if key not in valid_keys:
        console.print(f"[red]Invalid key. Valid keys: {', '.join(sorted(valid_keys))}[/red]")
        raise typer.Exit(1)

    if key == "max_tokens":
        try:
            parsed_max_tokens = int(value)
        except ValueError:
            console.print("[red]max_tokens must be an integer[/red]")
            raise typer.Exit(1)
        if parsed_max_tokens <= 0:
            console.print("[red]max_tokens must be greater than 0[/red]")
            raise typer.Exit(1)
        setattr(config, key, parsed_max_tokens)
    elif key == "temperature":
        try:
            parsed_temperature = float(value)
        except ValueError:
            console.print("[red]temperature must be a number[/red]")
            raise typer.Exit(1)
        if parsed_temperature < 0 or parsed_temperature > 2:
            console.print("[red]temperature must be between 0 and 2[/red]")
            raise typer.Exit(1)
        setattr(config, key, parsed_temperature)
    elif key == "agent_backend":
        normalized_value = value.strip()
        if not normalized_value:
            console.print("[red]agent_backend must be a non-empty provider key[/red]")
            raise typer.Exit(1)
        setattr(config, key, normalized_value)
    elif key == "agent_reasoning_effort":
        try:
            normalized_effort = normalize_reasoning_effort(value)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
        setattr(config, key, normalized_effort)
    elif key == "agent_parallel_tool_calls":
        normalized_value = value.strip().lower()
        if normalized_value not in {"1", "0", "true", "false", "yes", "no", "on", "off"}:
            console.print(
                "[red]agent_parallel_tool_calls must be one of: true, false, yes, no, on, off, 1, 0[/red]"
            )
            raise typer.Exit(1)
        setattr(config, key, normalized_value in {"1", "true", "yes", "on"})
    elif key == "agent_thinking_budget_tokens":
        try:
            parsed_budget = int(value)
        except ValueError:
            console.print("[red]agent_thinking_budget_tokens must be an integer[/red]")
            raise typer.Exit(1)
        if parsed_budget <= 0:
            console.print("[red]agent_thinking_budget_tokens must be greater than 0[/red]")
            raise typer.Exit(1)
        setattr(config, key, parsed_budget)
    else:
        setattr(config, key, value if value else None)

    try:
        save_config(config)
    except Exception as exc:
        console.print(f"[red]Failed to save config: {exc}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Set {key} = {value}[/green]")


def run_agent_dispatch(
    *,
    args: list[str],
    max_steps: int,
    yes: bool,
    model: str | None,
    sandbox: object,
    no_plugins: bool,
    response_json: bool,
    response_schema: object,
    input_file: list[object] | None,
    input_image: list[object] | None,
    console: Console,
    agent_setup_cmd: Callable[[], None],
    agent_status_cmd: Callable[[], None],
    agent_providers_cmd: Callable[[], None],
    run_agent_provider_setup_wizard: Callable[[str | None], Any],
    agent_resume_cmd: Callable[..., None],
    agent_reinstall_cmd: Callable[[str], None],
    agent_uninstall_cmd: Callable[..., None],
    run_agent_export_from_argv: Callable[[list[str]], None],
    run_agent_import_from_argv: Callable[[list[str]], None],
    run_agent_deploy_from_argv: Callable[[list[str]], None],
    run_agent_package_from_argv: Callable[[list[str]], None],
    run_agent_run_from_argv: Callable[..., None],
    agent_cmd: Callable[..., None],
) -> None:
    if not args:
        console.print(
            "[yellow]Usage: beep agent <goal> | beep agent setup | beep agent status[/yellow]"
        )
        raise typer.Exit(2)

    action = args[0].strip().lower()
    extra = args[1:]
    if action == "setup" and not extra:
        agent_setup_cmd()
        return
    if action == "status" and not extra:
        agent_status_cmd()
        return
    if action == "providers" and not extra:
        agent_providers_cmd()
        return
    if action == "configure":
        if len(extra) > 1:
            console.print("[yellow]Usage: beep agent configure [provider_key][/yellow]")
            raise typer.Exit(2)
        run_agent_provider_setup_wizard(extra[0] if extra else None)
        return
    if action == "resume":
        if len(extra) != 1:
            console.print("[yellow]Usage: beep agent resume <thread_id>[/yellow]")
            raise typer.Exit(2)
        agent_resume_cmd(
            extra[0],
            max_steps=max_steps,
            auto_approve=yes,
            sandbox=sandbox,
            model=model,
            no_plugins=no_plugins,
            response_json=response_json,
            response_schema=response_schema,
            input_file=input_file,
            input_image=input_image,
        )
        return
    if action == "reinstall":
        if len(extra) != 1:
            console.print("[yellow]Usage: beep agent reinstall <package|runtime>[/yellow]")
            raise typer.Exit(2)
        agent_reinstall_cmd(extra[0])
        return
    if action == "uninstall" and not extra:
        agent_uninstall_cmd(yes=yes)
        return
    if action == "export":
        if not extra:
            console.print("[yellow]Usage: beep agent export <agent_id> [options][/yellow]")
            raise typer.Exit(2)
        run_agent_export_from_argv(extra)
        return
    if action == "import":
        if not extra:
            console.print("[yellow]Usage: beep agent import <bundle_file> [options][/yellow]")
            raise typer.Exit(2)
        run_agent_import_from_argv(extra)
        return
    if action == "deploy":
        if not extra:
            console.print("[yellow]Usage: beep agent deploy <bundle_file_or_id> [options][/yellow]")
            raise typer.Exit(2)
        run_agent_deploy_from_argv(extra)
        return
    if action == "package":
        if not extra:
            console.print("[yellow]Usage: beep agent package <bundle_file_or_id> [options][/yellow]")
            raise typer.Exit(2)
        run_agent_package_from_argv(extra)
        return
    if action == "run":
        if len(extra) < 2:
            console.print("[yellow]Usage: beep agent run <bundle_file_or_id> <goal>[/yellow]")
            raise typer.Exit(2)
        run_agent_run_from_argv(
            extra[0],
            extra[1:],
            max_steps=max_steps,
            auto_approve=yes,
            sandbox=sandbox,
            model=model,
            no_plugins=no_plugins,
            response_json=response_json,
            response_schema=response_schema,
            input_file=input_file,
            input_image=input_image,
        )
        return

    goal = " ".join(args).strip()
    agent_cmd(
        goal,
        max_steps=max_steps,
        auto_approve=yes,
        sandbox=sandbox,
        model=model,
        no_plugins=no_plugins,
        response_json=response_json,
        response_schema=response_schema,
        input_file=input_file,
        input_image=input_image,
    )
