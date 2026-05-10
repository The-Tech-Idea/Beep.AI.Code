"""Agent command: /agent."""

from __future__ import annotations

from typing import Any


from beep.chat.commands._budget import ensure_budget_available
from beep.chat.commands.base import Command
from beep.mcp.discovery import resolve_mcp_configuration
from beep.permissions.manager import coerce_sandbox_mode



from beep.utils.console import get_console
class AgentCommand(Command):
    @property
    def name(self) -> str:
        return "agent"

    @property
    def description(self) -> str:
        return "Run autonomous agent"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /agent <goal>[/yellow]")
            return
        from beep.agent.loop import run_agent
        config = ctx.get("config")
        session = ctx.get("session")
        plugins_enabled = True
        coding_meta: dict[str, Any] | None = None
        workspace_root = getattr(session, "_workspace", None) if session is not None else None
        if session is not None and not ensure_budget_available(session, command="agent"):
            return
        if session is not None and hasattr(session, "plugins_enabled"):
            plugins_enabled = bool(session.plugins_enabled)
        if session is not None and hasattr(session, "_get_coding_metadata"):
            raw_meta = session._get_coding_metadata()
            if isinstance(raw_meta, dict) and raw_meta:
                coding_meta = dict(raw_meta)
                coding_meta["interaction_mode"] = "agent"
        sandbox_mode = coerce_sandbox_mode(
            getattr(session, "_sandbox_mode", getattr(session, "_sandbox", False))
        ) if session is not None else coerce_sandbox_mode(None)
        resolved_mcp = resolve_mcp_configuration(config, workspace_root) if config is not None else None
        await run_agent(
            ctx["client"],
            args,
            config=config,
            workspace_root=workspace_root,
            auto_approve=False,
            sandbox_mode=sandbox_mode,
            plugins_enabled=plugins_enabled,
            coding_assistant=coding_meta,
            mcp_enabled=resolved_mcp.enabled if resolved_mcp is not None else bool(getattr(config, "mcp_enabled", False)),
            mcp_servers=resolved_mcp.servers if resolved_mcp is not None else getattr(config, "mcp_servers", []) or [],
        )
