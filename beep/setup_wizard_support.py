"""Shared helper logic for the interactive setup wizard."""

from __future__ import annotations

import os
from typing import Any, Callable


from beep.config import BeepConfig


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def mask_secret(value: str | None) -> str:
    if value is None:
        return "Not set"
    return "****" + value[-4:] if len(value) >= 4 else "****"


def supports_interactive_provider_setup(guidance: object) -> bool:
    return bool(
        getattr(guidance, "key", None) == "beep"
        or getattr(guidance, "requires_api_key", None) is not None
        or getattr(guidance, "requires_model", None) is not None
        or getattr(guidance, "default_base_url", None) is not None
    )


def prompt_required_text(
    *,
    ask: Callable[..., str],
    console: Console,
    label: str,
    current_value: str | None,
    required_message: str,
    normalize_url: bool = False,
) -> str:
    while True:
        response = ask(
            label,
            default=current_value or "",
            show_default=bool(current_value),
        )
        normalized = normalize_optional_text(response)
        if normalized is not None:
            return normalized.rstrip("/") if normalize_url else normalized
        console.print(f"[yellow]{required_message}[/yellow]")


def prompt_secret_value(
    *,
    ask: Callable[..., str],
    console: Console,
    label: str,
    current_value: str | None,
    required: bool,
    required_message: str,
) -> str | None:
    lowered_label = label.strip().lower()
    if current_value:
        console.print(f"[dim]Current {lowered_label}: {mask_secret(current_value)}[/dim]")
        if ask(f"  Change {lowered_label}?", choices=["y", "n"], default="n") == "n":
            return current_value
    while True:
        value = normalize_optional_text(ask(label, password=True))
        if value is not None:
            return value
        if not required:
            return None
        console.print(f"[yellow]{required_message}[/yellow]")


async def test_connection(
    config: BeepConfig,
    *,
    client_factory: Callable[[BeepConfig], Any],
) -> tuple[bool, str]:
    """Test server connection and return (success, status_message)."""
    try:
        client = client_factory(config)
        health = await client.health_check()
        await client.close()
        status = health.get("status", "unknown")
        return True, f"Status: {status}"
    except Exception as exc:
        return False, str(exc)


async def test_token(
    config: BeepConfig,
    *,
    client_factory: Callable[[BeepConfig], Any],
) -> tuple[bool, str]:
    """Test API token validity and return (success, message)."""
    try:
        client = client_factory(config)
        result = await client.check_token()
        await client.close()
        if result.get("valid"):
            app = result.get("application", {})
            name = app.get("name", "unknown")
            scopes = result.get("scopes", [])
            scope_str = ", ".join(scopes) if scopes else "none"
            return True, f"App: {name} | Scopes: {scope_str}"
        return False, result.get("error", "Token invalid")
    except Exception as exc:
        return False, str(exc)


def ensure_configured_impl(
    *,
    load_config: Callable[[], BeepConfig],
    ask: Callable[..., str],
    console: Console,
    run_setup_wizard: Callable[[], BeepConfig],
) -> BeepConfig:
    """Ensure configuration exists, running the setup wizard when needed."""
    config = load_config()

    has_env_token = bool(os.environ.get("BEEP_API_TOKEN"))
    has_env_url = bool(os.environ.get("BEEP_SERVER_URL"))
    if has_env_token and has_env_url:
        return config
    if config.is_configured:
        return config

    console.print()
    console.print("[yellow]Beep.AI.Code is not configured.[/yellow]")
    console.print("[dim]Run 'beep setup' to configure manually.[/dim]")
    console.print()

    try:
        answer = ask("Run setup wizard now?", choices=["y", "n"], default="y")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Setup cancelled[/yellow]")
        raise SystemExit(1)

    if answer.lower() != "y":
        console.print("[yellow]Run 'beep setup' when ready[/yellow]")
        raise SystemExit(1)

    try:
        return run_setup_wizard()
    except SystemExit:
        raise
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Setup cancelled[/yellow]")
        raise SystemExit(1)


def ensure_agent_configured_impl(
    *,
    load_config: Callable[[], BeepConfig],
    find_workspace_root: Callable[[], Any],
    load_runtime_plugins: Callable[[Any], Any],
    is_agent_backend_configured: Callable[..., bool],
    describe_agent_provider_guidance: Callable[..., Any],
    supports_interactive_provider_setup: Callable[[object], bool],
    run_agent_provider_setup_wizard: Callable[[str | None], BeepConfig],
) -> BeepConfig:
    """Ensure the autonomous agent backend has enough configuration to run."""
    config = load_config()
    plugin_registry = load_runtime_plugins(find_workspace_root()).registry
    if is_agent_backend_configured(config, plugin_registry=plugin_registry):
        return config

    guidance = describe_agent_provider_guidance(config, plugin_registry=plugin_registry)
    if supports_interactive_provider_setup(guidance):
        return run_agent_provider_setup_wizard(config.agent_backend)

    raise RuntimeError(
        f"Agent backend '{config.agent_backend}' is not configured. Configure the provider's required settings via `beep config-set` or the provider plugin's documented setup."
    )
