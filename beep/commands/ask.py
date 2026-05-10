"""Ask command for one-shot queries."""

from __future__ import annotations

import typer

from beep.chat.stream_renderer import render_response
from beep.coding.metadata import build_coding_metadata
from beep.coding.prompt_context import build_workspace_system_prompt
from beep.workspace.detector import find_workspace_root
from beep.utils.console import get_console
from beep.cli_support_async import run_async_cmd


def ask_cmd(
    question: str = typer.Argument(..., help="Question to ask"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
    mode: str = typer.Option("assistant", "--mode", help="Chat mode: assistant, review, explain"),
) -> None:
    """Ask a one-shot question."""
    from beep.app_service import get_app_service
    from beep.setup_wizard import ensure_configured

    config = ensure_configured()

    async def _run() -> None:
        client = get_app_service().api_client(config)
        workspace_root = find_workspace_root()
        messages = [
            {
                "role": "system",
                "content": build_workspace_system_prompt(mode, workspace_root),
            },
            {"role": "user", "content": question},
        ]
        response = await client.chat_completion(
            messages=messages,
            model=model,
            coding_assistant=build_coding_metadata(
                workspace_root=workspace_root,
                interaction_mode="inline",
                project_id=config.project_id,
            ),
        )
        choices = response.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content.strip():
                render_response(content)
            else:
                get_console().print("[yellow]Model returned an empty response[/yellow]")
        else:
            get_console().print("[yellow]Model returned no choices[/yellow]")

        usage = response.get("usage")
        if usage:
            get_console().print(
                f"[dim]Tokens: {usage.get('prompt_tokens', '?')} prompt + "
                f"{usage.get('completion_tokens', '?')} completion = "
                f"{usage.get('total_tokens', '?')} total[/dim]"
            )

    run_async_cmd(_run, cancel_message="Ask cancelled")
