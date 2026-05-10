"""Interactive setup flow implementations for Beep.AI.Code."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from rich.console import Console

from beep.config import BeepConfig

PromptAsk = Callable[..., str]
PanelFit = Callable[..., Any]
ConfigLoader = Callable[[], BeepConfig]
ConfigSaver = Callable[[BeepConfig], None]
ConfigProbe = Callable[[BeepConfig], Awaitable[tuple[bool, str]]]
WorkspaceRootResolver = Callable[[], Any]
RuntimePluginLoader = Callable[[Any], Any]
ProviderGuidanceResolver = Callable[..., Any]
ProviderGuidanceLister = Callable[..., list[Any]]
ProviderConfigurationProbe = Callable[..., Awaitable[Any]]
BackendConfiguredPredicate = Callable[..., bool]
OptionalTextNormalizer = Callable[[str | None], str | None]
InteractiveSetupSupportPredicate = Callable[[object], bool]
RequiredTextPrompter = Callable[..., str]
SecretValuePrompter = Callable[..., str | None]


@dataclass(frozen=True)
class SetupWizardFlowDependencies:
    console: Console
    ask: PromptAsk
    panel_fit: PanelFit
    load_config: ConfigLoader
    save_config: ConfigSaver
    config_file: Any
    test_connection: ConfigProbe
    test_token: ConfigProbe


@dataclass(frozen=True)
class AgentProviderSetupWizardDependencies:
    console: Console
    ask: PromptAsk
    panel_fit: PanelFit
    load_config: ConfigLoader
    save_config: ConfigSaver
    find_workspace_root: WorkspaceRootResolver
    load_runtime_plugins: RuntimePluginLoader
    describe_agent_provider_guidance: ProviderGuidanceResolver
    list_available_agent_provider_guidance: ProviderGuidanceLister
    probe_agent_backend_configuration: ProviderConfigurationProbe
    is_agent_backend_configured: BackendConfiguredPredicate
    normalize_optional_text: OptionalTextNormalizer
    supports_interactive_provider_setup: InteractiveSetupSupportPredicate
    prompt_required_text: RequiredTextPrompter
    prompt_secret_value: SecretValuePrompter
    run_setup_wizard: Callable[[], BeepConfig]


def run_setup_wizard_impl(
    *,
    dependencies: SetupWizardFlowDependencies,
) -> BeepConfig:
    """Run the interactive Beep.AI.Server configuration wizard."""
    console = dependencies.console
    ask = dependencies.ask
    panel_fit = dependencies.panel_fit

    console.print()
    console.print(
        panel_fit(
            "[bold blue]Beep.AI.Code Setup[/bold blue]\n\nConnect to your Beep.AI.Server instance",
            style="blue",
        )
    )
    console.print()

    existing = dependencies.load_config()

    console.print("[bold cyan]Step 1/3: Server URL[/bold cyan]")
    console.print("[dim]The URL where Beep.AI.Server is running[/dim]")
    console.print()

    server_url = ask(
        "  Server URL",
        default=existing.server_url,
        show_default=True,
    )
    server_url = server_url.rstrip("/")
    if not server_url.startswith(("http://", "https://")):
        server_url = "http://" + server_url

    console.print()
    console.print("[bold cyan]Step 2/3: API Token[/bold cyan]")
    console.print("[dim]Application token from Beep.AI.Server IAM settings[/dim]")
    console.print("[dim]Create one: Server Dashboard → IAM → Applications → Create Token[/dim]")
    console.print()

    if existing.api_token:
        masked = "****" + existing.api_token[-4:]
        console.print(f"[dim]Current token: {masked}[/dim]")
        if ask("  Change token?", choices=["y", "n"], default="n") == "n":
            api_token = existing.api_token
        else:
            api_token = ask("  API Token", password=True)
    else:
        api_token = ask("  API Token", password=True)

    if not api_token.strip():
        api_token = None

    console.print()
    console.print("[bold cyan]Step 3/3: Default Model (optional)[/bold cyan]")
    console.print("[dim]Leave empty to use the server's default model[/dim]")
    console.print()

    default_model = ask(
        "  Default model",
        default=existing.default_model or "",
        show_default=False,
    )
    if not default_model.strip():
        default_model = None

    config = BeepConfig(
        server_url=server_url,
        api_token=api_token,
        default_model=default_model,
        agent_backend=existing.agent_backend,
        agent_base_url=existing.agent_base_url,
        agent_api_key=existing.agent_api_key,
        agent_model=existing.agent_model,
        max_tokens=existing.max_tokens,
        temperature=existing.temperature,
        project_id=existing.project_id,
        mcp_enabled=existing.mcp_enabled,
        mcp_servers=existing.mcp_servers,
        request_timeout=existing.request_timeout,
        retry_on_429=existing.retry_on_429,
        max_retries=existing.max_retries,
    )

    console.print()
    with console.status("[bold]Testing server connection..."):
        success, message = asyncio.run(dependencies.test_connection(config))

    if success:
        console.print(f"  [green]✓ Server reachable — {message}[/green]")
    else:
        console.print(f"  [red]✗ Server unreachable — {message}[/red]")
        console.print()
        if ask("  Continue anyway?", choices=["y", "n"], default="n") == "n":
            console.print("[yellow]Setup cancelled[/yellow]")
            raise SystemExit(1)

    if api_token:
        with console.status("[bold]Validating API token..."):
            token_ok, token_msg = asyncio.run(dependencies.test_token(config))

        if token_ok:
            console.print(f"  [green]✓ Token valid — {token_msg}[/green]")
        else:
            console.print(f"  [yellow]⚠ Token check failed — {token_msg}[/yellow]")
            console.print("[dim](Server may not have token check endpoint)[/dim]")

    dependencies.save_config(config)
    console.print()
    console.print(
        panel_fit(
            f"[green]Configuration saved[/green]\n\n[dim]{dependencies.config_file}[/dim]",
            style="green",
        )
    )
    console.print()
    return config


def run_agent_provider_setup_wizard_impl(
    *,
    provider_key: str | None,
    dependencies: AgentProviderSetupWizardDependencies,
) -> BeepConfig:
    """Run an interactive setup flow for the selected autonomous-agent provider."""
    console = dependencies.console
    ask = dependencies.ask
    panel_fit = dependencies.panel_fit

    existing = dependencies.load_config()
    plugin_registry = dependencies.load_runtime_plugins(dependencies.find_workspace_root()).registry
    selected_key = dependencies.normalize_optional_text(provider_key) or existing.agent_backend

    try:
        guidance = dependencies.describe_agent_provider_guidance(
            existing,
            provider_key=selected_key,
            plugin_registry=plugin_registry,
        )
    except ValueError:
        providers = dependencies.list_available_agent_provider_guidance(
            existing,
            plugin_registry=plugin_registry,
        )
        console.print(f"[red]Unsupported agent backend: {selected_key}[/red]")
        console.print(
            "[dim]Available providers: "
            + ", ".join(provider.key for provider in providers)
            + "[/dim]"
        )
        raise SystemExit(1)

    if not dependencies.supports_interactive_provider_setup(guidance):
        raise RuntimeError(
            f"Agent backend '{guidance.key}' does not expose enough setup metadata for the interactive wizard. Configure the provider's required settings via `beep config-set` or the provider plugin's documented setup."
        )

    if guidance.key == "beep":
        config = dependencies.run_setup_wizard()
        if config.agent_backend != "beep":
            config.agent_backend = "beep"
            dependencies.save_config(config)
        return config

    console.print()
    console.print(
        panel_fit(
            f"[bold blue]Agent Provider Setup[/bold blue]\n\nConfigure {guidance.display_name} ({guidance.key})",
            style="blue",
        )
    )
    console.print(f"[dim]Source: {guidance.source}[/dim]")
    for note in guidance.notes:
        console.print(f"[dim]- {note}[/dim]")

    config = existing.model_copy(deep=True)
    config.agent_backend = guidance.key

    console.print()
    console.print("[bold cyan]Connection[/bold cyan]")
    if guidance.default_base_url is not None:
        if config.agent_base_url:
            console.print(
                f"[dim]Current agent base URL override: {config.agent_base_url.rstrip('/')}[/dim]"
            )
        console.print(f"[dim]Default base URL: {guidance.default_base_url}[/dim]")
        base_url_override = ask(
            "  Agent base URL override (leave empty to use the provider default)",
            default=config.agent_base_url or "",
            show_default=bool(config.agent_base_url),
        )
        config.agent_base_url = dependencies.normalize_optional_text(base_url_override)
        if config.agent_base_url is not None:
            config.agent_base_url = config.agent_base_url.rstrip("/")
    else:
        config.agent_base_url = dependencies.prompt_required_text(
            "  Agent base URL",
            current_value=config.agent_base_url,
            required_message="Agent base URL is required for this provider.",
            normalize_url=True,
        )

    if guidance.requires_api_key:
        console.print()
        console.print("[bold cyan]Authentication[/bold cyan]")
        config.agent_api_key = dependencies.prompt_secret_value(
            "  Agent API key",
            current_value=config.agent_api_key,
            required=True,
            required_message="Agent API key is required for this provider.",
        )

    if guidance.requires_model:
        console.print()
        console.print("[bold cyan]Model[/bold cyan]")
        config.agent_model = dependencies.prompt_required_text(
            "  Agent model",
            current_value=config.agent_model or config.default_model,
            required_message="Agent model is required for this provider.",
        )

    if not dependencies.is_agent_backend_configured(config, plugin_registry=plugin_registry):
        raise RuntimeError(
            f"Agent backend '{guidance.key}' is still not configured after setup. Configure the remaining settings via `beep config-set` or the provider plugin's documented setup."
        )

    with console.status("[bold]Validating agent provider...[/bold]"):
        probe_result = asyncio.run(
            dependencies.probe_agent_backend_configuration(config, plugin_registry=plugin_registry)
        )

    if probe_result.supported:
        if probe_result.success:
            console.print(f"  [green]✓ Provider reachable — {probe_result.message}[/green]")
        else:
            console.print(f"  [yellow]⚠ Provider probe failed — {probe_result.message}[/yellow]")
            console.print()
            if ask("  Continue anyway?", choices=["y", "n"], default="n") == "n":
                console.print("[yellow]Setup cancelled[/yellow]")
                raise SystemExit(1)
    else:
        console.print(f"[dim]Skipping provider validation — {probe_result.message}[/dim]")

    dependencies.save_config(config)
    console.print()
    console.print(
        panel_fit(
            f"[green]Agent provider configuration saved[/green]\n\n[dim]{guidance.display_name} ({guidance.key})[/dim]",
            style="green",
        )
    )
    console.print()
    return config
