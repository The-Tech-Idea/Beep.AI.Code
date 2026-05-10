"""Chat commands for Beep.AI.Code CLI."""

from __future__ import annotations

import typer

from beep.chat.runner import run_chat
from beep.cli_support_async import run_async_cmd


def chat_cmd(
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
    mode: str = typer.Option("assistant", "--mode", help="Chat mode: assistant, review, explain"),
    show_tokens: bool = typer.Option(False, "--tokens", help="Show token usage"),
    resume: str | None = typer.Option(None, "--resume", "-r", help="Resume a session"),
    no_plugins: bool = typer.Option(False, "--no-plugins", help="Disable plugin loading"),
) -> None:
    """Start interactive chat session."""
    from beep.app_service import get_app_service
    from beep.setup_wizard import ensure_configured

    config = ensure_configured()

    async def _run() -> None:
        client = get_app_service().api_client(config)
        await run_chat(
            client,
            model=model,
            mode=mode,
            show_tokens=show_tokens,
            resume_session=resume,
            plugins_enabled=not no_plugins,
            config=config,
        )

    run_async_cmd(_run, cancel_message="Chat ended")
