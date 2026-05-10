"""Streaming response renderer using Rich."""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner

from beep.api.streaming import TOOL_CALL_PREFIX, TOOL_CALL_SUFFIX


from beep.utils.console import get_console
_TOOL_CALL_RE = re.compile(
    re.escape(TOOL_CALL_PREFIX) + r"([^\x00]+)" + re.escape(TOOL_CALL_SUFFIX)
)


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Extract code blocks from markdown text.

    Returns list of (language, code) tuples.
    """
    blocks = []
    pattern = r"```(\w*)\n(.*?)```"
    for match in re.finditer(pattern, text, re.DOTALL):
        lang = match.group(1) or "text"
        code = match.group(2)
        blocks.append((lang, code))
    return blocks


async def render_stream(
    stream: AsyncGenerator[str, None],
    *,
    title: str = "Assistant",
) -> str:
    """Render a streaming response with Rich live display.

    Tool-call marker chunks (``\\x00TC:name\\x00``) are rendered inline as
    ``[tool: name(...)]`` and are stripped from the returned text.

    If the user presses Ctrl-C during streaming, the partial response is
    returned with a ``\\n[cancelled by user]`` suffix so the conversation
    remains consistent.

    Args:
        stream: Async generator yielding text chunks
        title: Panel title

    Returns:
        Complete response text (excluding tool-call markers).
    """
    full_text = ""
    spinner = Spinner("dots", text="Thinking...")

    try:
        with Live(spinner, console=get_console(), refresh_per_second=10) as live:
            async for chunk in stream:
                # Detect and render tool-call markers inline
                tool_match = _TOOL_CALL_RE.search(chunk)
                if tool_match:
                    tool_name = tool_match.group(1)
                    get_console().print(f"[dim][tool: {tool_name}(...)][/dim]")
                    chunk = _TOOL_CALL_RE.sub("", chunk)
                    if not chunk:
                        continue

                full_text += chunk
                if len(full_text) < 50:
                    continue
                live.update(
                    Panel(
                        Markdown(full_text),
                        title=title,
                        border_style="blue",
                        padding=(1, 2),
                    )
                )
    except KeyboardInterrupt:
        full_text += "\n[cancelled by user]"
        get_console().print("\n[yellow]Cancelled[/yellow]")

    if full_text:
        get_console().print()

    return full_text


def render_response(text: str, *, title: str = "Assistant") -> None:
    """Render a complete response."""
    get_console().print(
        Panel(
            Markdown(text),
            title=title,
            border_style="blue",
            padding=(1, 2),
        )
    )


def render_token_usage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    """Render token usage statistics."""
    get_console().print(
        f"[dim]Tokens: {prompt_tokens} prompt + "
        f"{completion_tokens} completion = "
        f"{total_tokens} total[/dim]"
    )
