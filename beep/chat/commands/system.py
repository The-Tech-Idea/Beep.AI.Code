"""System commands: /status, /config, /diagnostics, /templates."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command
from beep.config import CONFIG_FILE, load_config
from beep.system_support import (
    build_chat_config_rows,
    collect_chat_diagnostics_state,
    render_chat_diagnostics_state,
    render_health_status,
    render_key_value_table,
)
from beep.workspace.detector import find_workspace_root
from beep.workspace.git import is_git_repo


from beep.utils.console import get_console


class StatusCommand(Command):
    @property
    def name(self) -> str:
        return "status"

    @property
    def description(self) -> str:
        return "Server health"

    @property
    def category(self) -> str:
        return "System"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        client = ctx["client"]
        if client._config.api_token:
            try:
                health = await client.v1_health()
            except Exception:
                health = await client.health_check()
        else:
            health = await client.health_check()
        render_health_status(
            health=health,
            console=get_console(),
            title="Server Status",
        )


class ConfigCommand(Command):
    @property
    def name(self) -> str:
        return "config"

    @property
    def description(self) -> str:
        return "Show configuration"

    @property
    def category(self) -> str:
        return "System"

    async def execute(self, _args: str, _ctx: dict[str, Any]) -> None:
        config = load_config()
        render_key_value_table(
            title="Configuration",
            key_header="Setting",
            value_header="Value",
            rows=build_chat_config_rows(config=config, config_file=CONFIG_FILE),
            console=get_console(),
        )


class DiagnosticsCommand(Command):
    @property
    def name(self) -> str:
        return "diagnostics"

    @property
    def description(self) -> str:
        return "System info"

    @property
    def category(self) -> str:
        return "System"

    async def execute(self, _args: str, ctx: dict[str, Any]) -> None:
        from beep import __version__

        state = collect_chat_diagnostics_state(
            session=ctx["session"],
            workspace_root=find_workspace_root(),
            version=__version__,
            git_repo_lookup=is_git_repo,
        )
        render_chat_diagnostics_state(state=state, console=get_console())


class TemplatesCommand(Command):
    @property
    def name(self) -> str:
        return "templates"

    @property
    def description(self) -> str:
        return "List code templates"

    @property
    def category(self) -> str:
        return "System"

    async def execute(self, _args: str, _ctx: dict[str, Any]) -> None:
        from beep.templates.generator import display_templates, list_templates
        from beep.templates.service import show_template_listing

        show_template_listing(
            workspace_root=find_workspace_root(),
            category=None,
            list_templates=list_templates,
            display_templates=display_templates,
        )
