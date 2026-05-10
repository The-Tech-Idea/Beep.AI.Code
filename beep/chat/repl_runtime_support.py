"""Runtime and command helpers for the interactive chat REPL."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.prompt import Prompt

from beep.chat.session_runtime_state import get_session_mcp_runtime
from beep.workspace.editing import prepare_workspace_edit
from beep.workspace.file_ops import apply_edit
from beep.utils.console import get_console

if TYPE_CHECKING:
    from beep.chat.repl import ChatSession


def _print_hook_outputs(outputs: list[str], console: Console) -> None:
    """Print hook execution outputs in dim style."""
    for line in outputs:
        console.print(f"[dim]{line}[/dim]")


def _handle_memory_after_turn(session: ChatSession, console: Console) -> None:
    """Check session memory after each turn; warn or trigger auto-compact."""
    # Always emit an inline warning if thresholds are crossed
    session._check_memory_after_turn()

    watcher = getattr(session, "_memory_watcher", None)
    auto_compact = getattr(session, "_auto_compact", True)

    if watcher is None or not auto_compact:
        return

    if not watcher.should_auto_compact(session._messages):
        return

    # Auto-compact runs in the background — fire-and-forget (sync trim only to
    # keep the turn latency zero; the user can /compact for LLM summarization).
    import asyncio
    from beep.sessions.compactor import compact_session
    from beep.sessions.history import HISTORY_DIR, replace_session

    session_file = HISTORY_DIR / f"{session._session_id}.jsonl"

    async def _do_compact() -> None:
        result = await compact_session(
            session._messages,
            strategy="trim",
            session_file=session_file,
        )
        session._messages = result.messages
        replace_session(session._session_id, session._messages)
        watcher.reset()
        console.print(
            f"[dim]Auto-compacted: {result.stats_before.message_count} → "
            f"{result.stats_after.message_count} messages "
            f"({result.stats_before.token_k:.1f}k → {result.stats_after.token_k:.1f}k tokens)[/dim]"
        )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_do_compact())
        else:
            loop.run_until_complete(_do_compact())
    except Exception:
        pass


async def bootstrap_workspace(
    session: ChatSession,
    *,
    console: Console,
    log_event: Any,
    bootstrap_coding_workspace: Any,
) -> None:
    if not session._coding_enabled:
        return
    try:
        session._coding_project_id, session._coding_session_id = await bootstrap_coding_workspace(
            session._client,
            workspace=session._workspace,
            config=session._config,
            model=session._model,
            console=get_console(),
        )
    except Exception as exc:
        console.print(f"[dim]Workspace bootstrap skipped: {exc}[/dim]")
        log_event("coding.bootstrap.error", error=str(exc))


async def send(
    session: ChatSession,
    user_input: str,
    *,
    console: Console,
    log_event: Any,
    stream_assistant_turn: Any,
    build_rules_context: Any,
) -> None:
    from beep.hooks.manager import run_hooks

    budget = session._max_token_budget
    if budget is not None and session._token_count >= budget:
        console.print(
            "[yellow]Token budget reached. Increase with /max_tokens "
            "or start a new session.[/yellow]"
        )
        log_event(
            "chat.request.blocked_budget",
            session_id=session._session_id,
            token_count=session._token_count,
            token_budget=budget,
        )
        return

    _print_hook_outputs(run_hooks("pre_send", session.hook_config), console)

    cleaned, included = session._context.resolve_mentions(user_input)

    # Build automatic workspace context when enabled.
    auto_context_text = ""
    auto_sources: list[str] = []
    if getattr(session, "_auto_context_enabled", True):
        try:
            from beep.context.auto_context import build_auto_context

            result = build_auto_context(
                cleaned,
                workspace_root=session._workspace,
                semantic_search_adapter=getattr(session, "_semantic_search_adapter", None),
            )
            auto_context_text = result.context_text
            auto_sources = result.sources
        except Exception:
            pass

    pinned_context = session._context.build_context()
    skill_context = session._build_skill_context(cleaned)
    rules_context = build_rules_context(session._rules)
    segments = []
    if auto_context_text:
        segments.append(auto_context_text)
    if pinned_context:
        segments.append(pinned_context)
    if rules_context:
        segments.append(rules_context)
    if skill_context:
        segments.append(skill_context)
    segments.append(cleaned)
    full_input = "\n\n".join(segments)

    if included:
        console.print(f"[dim]Included: {', '.join(included)}[/dim]")
    if auto_sources:
        console.print(f"[dim]Auto-context: {', '.join(auto_sources)}[/dim]")

    session._messages.append({"role": "user", "content": full_input})
    session._save("user", user_input)
    await stream_assistant_turn(
        session=session,
        client=session._client,
        event="request",
        empty_message="[yellow]Model returned an empty response[/yellow]",
        empty_error="empty_response",
    )

    _print_hook_outputs(run_hooks("post_send", session.hook_config), console)

    # Memory check: warn or auto-compact after the assistant has replied.
    _handle_memory_after_turn(session, console)


def update_coding_ids(
    session: ChatSession,
    response: str,
    *,
    log_event: Any,
    find_coding_identity: Any,
) -> None:
    project_id, session_id = find_coding_identity(response)
    if project_id is None and session_id is None:
        return

    if project_id is not None:
        session._coding_project_id = project_id
    if session_id:
        session._coding_session_id = session_id

    log_event(
        "coding.ids.updated",
        project_id=session._coding_project_id,
        session_id=session._coding_session_id,
    )


def handle_coding_approvals(
    session: ChatSession,
    response_text: str,
    *,
    console: Console,
    log_event: Any,
    count_pending_approvals: Any,
) -> None:
    pending_count = count_pending_approvals(response_text)
    if pending_count <= 0:
        return

    console.print(
        f"[yellow]Pending coding approvals detected: {pending_count}. "
        "Review server-side changes before continuing.[/yellow]"
    )
    log_event("coding.approvals.pending", count=pending_count, session_id=session._session_id)


async def run(
    session: ChatSession,
    *,
    console: Console,
    read_multiline: Any,
) -> None:
    from beep.hooks.manager import run_hooks

    hook_config = session.hook_config
    _print_hook_outputs(run_hooks("session_start", hook_config), console)

    await session._bootstrap_workspace()
    session._show_welcome()

    while True:
        if session._edit_target:
            console.print(
                f"[yellow]Enter content for {session._edit_target} (empty line to finish):[/yellow]"
            )
            lines = []
            while True:
                try:
                    line = Prompt.ask("  ...")
                except (KeyboardInterrupt, EOFError):
                    break
                if not line:
                    break
                lines.append(line)
            if lines:
                content = "\n".join(lines)
                prepared_edit = prepare_workspace_edit(session._edit_target, new_content=content)
                session._last_edit = prepared_edit.to_undo_record()
                apply_edit(
                    prepared_edit.path,
                    prepared_edit.old_content,
                    prepared_edit.new_content,
                    require_confirm=True,
                )
            session._edit_target = None
            continue

        user_input = read_multiline(
            commands={name: cmd.description for name, cmd in session._commands.items()},
            workspace_root=session._workspace,
        )
        if user_input is None:
            console.print()
            _print_hook_outputs(run_hooks("session_end", hook_config), console)
            break

        if user_input.startswith("/"):
            await session._handle_command(user_input)
            continue

        await session.send(user_input)


async def handle_command(
    session: ChatSession,
    command: str,
    *,
    console: Console,
    log_event: Any,
) -> None:
    from beep.hooks.manager import run_hooks

    parts = command.split(maxsplit=1)
    cmd_name = parts[0].lower().lstrip("/")
    args = parts[1].strip() if len(parts) > 1 else ""

    cmd = session._commands.get(cmd_name)
    if not cmd:
        try:
            response = await session._plugin_runtime.registry.handle_plugin_command(cmd_name, args)
        except Exception as exc:
            console.print(f"[red]Plugin command error: {exc}[/red]")
            log_event(
                "chat.command.plugin.error",
                session_id=session._session_id,
                command=cmd_name,
                error=str(exc),
            )
            return
        if response is not None:
            log_event(
                "chat.command.plugin.success",
                session_id=session._session_id,
                command=cmd_name,
            )
            console.print(response)
            return
        log_event(
            "chat.command.unknown",
            session_id=session._session_id,
            command=cmd_name,
        )
        console.print(f"[yellow]Unknown command: /{cmd_name}[/yellow]")
        return

    _print_hook_outputs(run_hooks("pre_command", session.hook_config), console)

    ctx: dict[str, Any] = {
        "client": session._client,
        "session": session,
        "session_id": session._session_id,
        "chat_context": session._context,
        "command_registry": session._commands,
        "config": session._config,
        "plugin_runtime": session._plugin_runtime,
        "plugin_commands": session._plugin_commands,
    }
    mcp_runtime = get_session_mcp_runtime(session)
    ctx["mcp_runtime"] = mcp_runtime
    if mcp_runtime.resolution is not None:
        ctx["mcp_resolution"] = mcp_runtime.resolution
    if mcp_runtime.client is not None:
        ctx["mcp_client"] = mcp_runtime.client
    if mcp_runtime.resolution_error or mcp_runtime.client_error:
        log_event(
            "chat.command.mcp_context.error",
            session_id=session._session_id,
            resolution_error=mcp_runtime.resolution_error,
            client_error=mcp_runtime.client_error,
        )

    log_event(
        "chat.command.start",
        session_id=session._session_id,
        command=cmd_name,
    )
    try:
        await cmd.execute(args, ctx)
        log_event(
            "chat.command.success",
            session_id=session._session_id,
            command=cmd_name,
        )
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        console.print(f"[red]Command error: {exc}[/red]")
        log_event(
            "chat.command.error",
            session_id=session._session_id,
            command=cmd_name,
            error=str(exc),
        )
    finally:
        _print_hook_outputs(run_hooks("post_command", session.hook_config), console)
