"""Interactive chat runner entrypoint."""

from __future__ import annotations

from typing import Any

from beep.api.client import BeepAPIClient
from beep.chat.repl import ChatSession


async def run_chat(
    client: BeepAPIClient,
    *,
    model: str | None = None,
    mode: str = "assistant",
    show_tokens: bool = False,
    plugins_enabled: bool = True,
    resume_session: str | None = None,
    config: Any = None,
) -> None:
    session = ChatSession(
        client,
        model=model,
        mode=mode,
        show_tokens=show_tokens,
        plugins_enabled=plugins_enabled,
        config=config,
    )
    if resume_session:
        session.resume_session(resume_session)
    await session.run()
