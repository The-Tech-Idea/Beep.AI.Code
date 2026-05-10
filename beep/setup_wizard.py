"""Interactive setup wizard for Beep.AI.Code."""

from __future__ import annotations

from rich.panel import Panel
from rich.prompt import Prompt

from beep.agent.provider_plugins import (
    describe_agent_provider_guidance,
    is_agent_backend_configured,
    list_available_agent_provider_guidance,
    probe_agent_backend_configuration,
)
from beep.api.client import BeepAPIClient
from beep.config import CONFIG_FILE, BeepConfig, load_config, save_config
from beep.plugins.runtime import load_runtime_plugins
from beep import setup_wizard_flows
from beep import setup_wizard_support
from beep.workspace.detector import find_workspace_root


from beep.utils.console import get_console


def _normalize_optional_text(value: str | None) -> str | None:
    return setup_wizard_support.normalize_optional_text(value)


def _mask_secret(value: str | None) -> str:
    return setup_wizard_support.mask_secret(value)


def _supports_interactive_provider_setup(guidance: object) -> bool:
    return setup_wizard_support.supports_interactive_provider_setup(guidance)


def _prompt_required_text(
    label: str,
    *,
    current_value: str | None,
    required_message: str,
    normalize_url: bool = False,
) -> str:
    return setup_wizard_support.prompt_required_text(
        ask=Prompt.ask,
        console=get_console(),
        label=label,
        current_value=current_value,
        required_message=required_message,
        normalize_url=normalize_url,
    )


def _prompt_secret_value(
    label: str,
    *,
    current_value: str | None,
    required: bool,
    required_message: str,
) -> str | None:
    return setup_wizard_support.prompt_secret_value(
        ask=Prompt.ask,
        console=get_console(),
        label=label,
        current_value=current_value,
        required=required,
        required_message=required_message,
    )


async def _test_connection(config: BeepConfig) -> tuple[bool, str]:
    return await setup_wizard_support.test_connection(
        config,
        client_factory=BeepAPIClient,
    )


async def _test_token(config: BeepConfig) -> tuple[bool, str]:
    return await setup_wizard_support.test_token(
        config,
        client_factory=BeepAPIClient,
    )


def run_setup_wizard() -> BeepConfig:
    """Run interactive setup wizard."""
    return setup_wizard_flows.run_setup_wizard_impl(
        dependencies=setup_wizard_flows.SetupWizardFlowDependencies(
            console=get_console(),
            ask=Prompt.ask,
            panel_fit=Panel.fit,
            load_config=load_config,
            save_config=save_config,
            config_file=CONFIG_FILE,
            test_connection=_test_connection,
            test_token=_test_token,
        ),
    )


def run_agent_provider_setup_wizard(provider_key: str | None = None) -> BeepConfig:
    """Run an interactive setup flow for the selected autonomous-agent provider."""
    return setup_wizard_flows.run_agent_provider_setup_wizard_impl(
        provider_key=provider_key,
        dependencies=setup_wizard_flows.AgentProviderSetupWizardDependencies(
            console=get_console(),
            ask=Prompt.ask,
            panel_fit=Panel.fit,
            load_config=load_config,
            save_config=save_config,
            find_workspace_root=find_workspace_root,
            load_runtime_plugins=load_runtime_plugins,
            describe_agent_provider_guidance=describe_agent_provider_guidance,
            list_available_agent_provider_guidance=list_available_agent_provider_guidance,
            probe_agent_backend_configuration=probe_agent_backend_configuration,
            is_agent_backend_configured=is_agent_backend_configured,
            normalize_optional_text=_normalize_optional_text,
            supports_interactive_provider_setup=_supports_interactive_provider_setup,
            prompt_required_text=_prompt_required_text,
            prompt_secret_value=_prompt_secret_value,
            run_setup_wizard=run_setup_wizard,
        ),
    )


def ensure_configured() -> BeepConfig:
    """Ensure configuration exists, running wizard if needed.

    Returns the loaded (or newly created) config.
    Exits if user cancels setup.
    """
    return setup_wizard_support.ensure_configured_impl(
        load_config=load_config,
        ask=Prompt.ask,
        console=get_console(),
        run_setup_wizard=run_setup_wizard,
    )


def ensure_agent_configured() -> BeepConfig:
    """Ensure the autonomous agent backend has enough configuration to run."""
    return setup_wizard_support.ensure_agent_configured_impl(
        load_config=load_config,
        find_workspace_root=find_workspace_root,
        load_runtime_plugins=load_runtime_plugins,
        is_agent_backend_configured=is_agent_backend_configured,
        describe_agent_provider_guidance=describe_agent_provider_guidance,
        supports_interactive_provider_setup=_supports_interactive_provider_setup,
        run_agent_provider_setup_wizard=run_agent_provider_setup_wizard,
    )
