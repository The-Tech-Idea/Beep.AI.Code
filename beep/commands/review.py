"""Review commands."""

from __future__ import annotations

import typer

from beep.chat.prompts import CODE_REVIEW
from beep.review.analyzer import (
    get_diff_to_review,
)
from beep.utils.console import get_console
from beep.cli_support_async import run_async_cmd


def review_cmd(
    staged: bool = typer.Option(True, "--staged", "-s", help="Review staged changes"),
    file: str | None = typer.Option(None, "--file", "-f", help="Review specific file"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use"),
) -> None:
    """Review code changes using AI."""
    from beep.app_service import get_app_service
    from beep.setup_wizard import ensure_configured
    from beep.workspace.detector import find_workspace_root

    config = ensure_configured()

    workspace_root = find_workspace_root()
    diff = get_diff_to_review(workspace_root, staged, file)

    if not diff:
        get_console().print("[yellow]No changes to review[/yellow]")
        return

    async def _run() -> None:
        client = get_app_service().api_client(config)
        messages = [
            {"role": "system", "content": CODE_REVIEW},
            {"role": "user", "content": f"Review this diff:\n\n```diff\n{diff}\n```"},
        ]
        response = await client.chat_completion(
            messages=messages,
            model=model or config.default_model,
        )
        choices = response.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content.strip():
                get_console().print(content)
            else:
                get_console().print("[yellow]Model returned an empty review[/yellow]")
        else:
            get_console().print("[yellow]Model returned no choices[/yellow]")

    run_async_cmd(_run, cancel_message="Review cancelled")
