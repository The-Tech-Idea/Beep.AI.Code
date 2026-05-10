"""Shared token budget guard for chat commands."""

from __future__ import annotations

from typing import Any


from beep.utils.json_logging import log_event



from beep.utils.console import get_console
def ensure_budget_available(session: Any, *, command: str) -> bool:
    """Return True when command execution is allowed within token budget."""
    budget = getattr(session, "_max_token_budget", None)
    token_count = int(getattr(session, "_token_count", 0) or 0)
    if budget is not None and token_count >= int(budget):
        get_console().print(
            "[yellow]Token budget reached. Increase with /max_tokens "
            "or start a new session.[/yellow]"
        )
        log_event(
            "chat.command.blocked_budget",
            session_id=getattr(session, "_session_id", ""),
            command=command,
            token_count=token_count,
            token_budget=int(budget),
        )
        return False
    return True
