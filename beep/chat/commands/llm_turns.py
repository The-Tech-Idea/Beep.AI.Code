"""Shared model-turn helpers for chat commands."""

from __future__ import annotations

from typing import Any


from beep.chat.commands.base import Command
from beep.chat.stream_renderer import render_response, render_stream, render_token_usage
from beep.utils.json_logging import log_event



from beep.utils.console import get_console
def get_coding_metadata(session: Any) -> dict[str, Any] | None:
    """Return Coding Assistant metadata when the session supports it."""
    if hasattr(session, "_get_coding_metadata"):
        metadata = session._get_coding_metadata()
        if isinstance(metadata, dict) and metadata:
            return metadata
    return None


def apply_text_response(
    session: Any,
    response: str,
    *,
    usage: dict[str, int] | None = None,
    coding_metadata: dict[str, Any] | None = None,
    save: bool = True,
) -> None:
    """Persist assistant output and update session bookkeeping."""
    if save:
        session._messages.append({"role": "assistant", "content": response})
        session._save("assistant", response)
    session._last_output = response[:10000]
    _apply_usage(session, response, usage)
    if coding_metadata and not getattr(session, "_coding_project_id", None):
        session._update_coding_ids(response)
    session._handle_coding_approvals(response)


async def stream_assistant_turn(
    *,
    session: Any,
    client: Any,
    event: str,
    title: str | None = None,
    empty_message: str | None = None,
    empty_error: str = "empty_response",
) -> str | None:
    """Stream one assistant turn and apply common session bookkeeping."""
    coding_metadata = get_coding_metadata(session)
    session._request_count += 1
    log_event(
        f"chat.{event}.start",
        session_id=getattr(session, "_session_id", ""),
        mode=getattr(session, "_mode", "assistant"),
        has_coding_metadata=bool(coding_metadata),
    )
    try:
        stream = client.chat_completion_stream(
            messages=session._messages,
            model=session._model,
            coding_assistant=coding_metadata,
        )
        response = await render_stream(stream, title=title or "Assistant")
        if empty_message and not response.strip():
            get_console().print(empty_message)
            log_event(
                f"chat.{event}.error",
                session_id=getattr(session, "_session_id", ""),
                error=empty_error,
            )
            return None
        usage = client.get_last_stream_usage() if hasattr(client, "get_last_stream_usage") else None
        apply_text_response(session, response, usage=usage, coding_metadata=coding_metadata)
        log_event(
            f"chat.{event}.success",
            session_id=getattr(session, "_session_id", ""),
            response_chars=len(response),
            estimated_tokens=getattr(session, "_token_count", 0),
        )
        return response
    except Exception as exc:
        get_console().print(f"[red]Error: {exc}[/red]")
        log_event(
            f"chat.{event}.error",
            session_id=getattr(session, "_session_id", ""),
            error=str(exc),
        )
        return None


async def complete_text_turn(
    *,
    session: Any,
    client: Any,
    messages: list[dict[str, Any]],
    event: str,
    max_tokens: int | None = None,
    empty_message: str | None = None,
    empty_error: str = "empty_response",
) -> str | None:
    """Run one non-streaming text completion and update common bookkeeping."""
    coding_metadata = get_coding_metadata(session)
    session._request_count += 1
    log_event(
        f"chat.{event}.start",
        session_id=getattr(session, "_session_id", ""),
        has_coding_metadata=bool(coding_metadata),
    )
    try:
        response = await client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            coding_assistant=coding_metadata,
        )
        choice = response.get("choices", [{}])[0]
        text: str = str(choice.get("message", {}).get("content", "")).strip()
        if empty_message and not text:
            get_console().print(empty_message)
            log_event(
                f"chat.{event}.error",
                session_id=getattr(session, "_session_id", ""),
                error=empty_error,
            )
            return None
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        apply_text_response(
            session,
            text,
            usage=_normalize_usage(usage),
            coding_metadata=coding_metadata,
            save=False,
        )
        log_event(
            f"chat.{event}.success",
            session_id=getattr(session, "_session_id", ""),
            response_chars=len(text),
            estimated_tokens=getattr(session, "_token_count", 0),
        )
        return text
    except Exception as exc:
        get_console().print(f"[red]Failed: {exc}[/red]")
        log_event(
            f"chat.{event}.error",
            session_id=getattr(session, "_session_id", ""),
            error=str(exc),
        )
        return None


def _apply_usage(session: Any, response: str, usage: dict[str, int] | None) -> None:
    if usage and usage.get("total_tokens", 0) > 0:
        session._token_count += usage["total_tokens"]
        if getattr(session, "_show_tokens", False):
            render_token_usage(
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                usage.get("total_tokens", 0),
            )
    else:
        session._token_count += len(response) // 4


def _normalize_usage(usage: dict[str, Any]) -> dict[str, int] | None:
    total = int(usage.get("total_tokens", 0) or 0)
    if total <= 0:
        return None
    return {
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": total,
    }


class AskCommand(Command):
    """One-shot question that does not pollute conversation history."""

    @property
    def name(self) -> str:
        return "ask"

    @property
    def description(self) -> str:
        return "One-shot question (no history)"

    @property
    def category(self) -> str:
        return "AI"

    async def execute(self, args: str, ctx: dict[str, Any]) -> None:
        if not args:
            get_console().print("[yellow]Usage: /ask <question>[/yellow]")
            return
        session = ctx["session"]
        client = ctx["client"]
        # Use only the system message + fresh user message — no history
        one_shot_messages: list[dict[str, Any]] = [
            session._messages[0],
            {"role": "user", "content": args},
        ]
        result = await complete_text_turn(
            session=session,
            client=client,
            messages=one_shot_messages,
            event="ask",
            empty_message="[yellow]No response[/yellow]",
            empty_error="empty_ask_response",
        )
        if result:
            render_response(result, title="Answer")
            # complete_text_turn already called apply_text_response(save=False);
            # undo that _last_output / _token_count update to session is acceptable
            # but we must NOT append to session._messages — complete_text_turn
            # already uses save=False so no history pollution occurs.
