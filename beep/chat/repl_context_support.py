"""Context and display helpers for the interactive chat REPL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from beep.chat.mode_state import AgentMode
from beep.coding.prompt_context import build_workspace_system_prompt

if TYPE_CHECKING:
    from beep.chat.repl import ChatSession


def build_system_prompt_content(session: ChatSession, mode: str) -> str:
    extra_sections = []
    plugin_context = session._plugin_runtime.registry.get_context().strip()
    if plugin_context:
        extra_sections.append("## Plugin Context\n\n" + plugin_context)

    agent_mode = getattr(session, "_agent_mode", AgentMode.BUILD)
    if agent_mode == AgentMode.PLAN:
        extra_sections.append(
            "## MODE: PLAN (Read-Only)\n\n"
            "You are operating in Plan mode. You can read files, search code, and answer "
            "questions, but you MUST NOT modify any files or run shell commands that write.\n"
            "Suggest changes and let the user approve them before switching to Build mode."
        )

    return build_workspace_system_prompt(
        mode,
        session._workspace,
        extra_sections=extra_sections,
    )


def resume_session(
    session: ChatSession,
    session_id: str,
    *,
    console: Console,
    load_session: Any,
) -> bool:
    messages = load_session(session_id)
    if not messages:
        console.print(f"[yellow]No history found: {session_id}[/yellow]")
        return False
    session._session_id = session_id
    session._messages = [
        {"role": "system", "content": session._build_system_prompt_content(session._mode)}
    ] + messages
    session._coding_project_id = None
    session._coding_session_id = None
    session._last_output = ""
    session._token_count = 0
    session._request_count = sum(1 for msg in messages if msg.get("role") == "user")
    console.print(f"[green]Resumed: {session_id} ({len(messages)} messages)[/green]")
    return True


def show_welcome(
    session: ChatSession,
    *,
    console: Console,
    is_git_repo: Any,
    get_git_status: Any,
) -> None:
    from rich.panel import Panel

    # ── Profile-aware welcome ────────────────────────────────────────
    profile_header = ""
    try:
        from beep.profiles import has_saved_profile, load_active_profile
        if has_saved_profile():
            profile = load_active_profile()
            if profile:
                profile_header = (
                    f"{profile.profile_icon} [bold]{profile.profile_display_name}[/bold] | "
                    f"[dim]{profile.model.model_id}[/dim]\n"
                )
    except ImportError:
        pass

    memory_info = ""
    if session._memory.global_instructions:
        memory_info = " | [yellow]project memory[/yellow]"

    git_info = ""
    if is_git_repo(session._workspace):
        status = get_git_status(session._workspace)
        if status:
            n = len(status.splitlines())
            git_info = f" | [dim]{n} changed[/dim]"

    pinned = session._context.pinned_files
    pin_info = ""
    if pinned:
        names = ", ".join(path.name for path in pinned)
        pin_info = f" | [dim]pinned: {names}[/dim]"

    coding_info = ""
    if session._coding_project_id:
        coding_info = f" | [green]coding: project {session._coding_project_id}[/green]"
    elif session._coding_enabled:
        coding_info = " | [yellow]coding: bootstrap pending[/yellow]"
    else:
        coding_info = " | [dim]coding: off[/dim]"

    plugin_count = len(session._plugin_runtime.registry.list_plugins())
    plugin_info = f" | [dim]plugins: {plugin_count}[/dim]"
    skill_info = f" | [dim]skills: {len(session._skills)}[/dim]"
    rule_info = f" | [dim]rules: {len(session._rules)}[/dim]"

    model_display = session._model or "[dim]default[/dim]"
    agent_mode = getattr(session, "_agent_mode", AgentMode.BUILD)
    mode_color = "blue" if agent_mode == AgentMode.PLAN else "green"
    mode_display = (
        f"[{mode_color}]Plan[/{mode_color}]"
        if agent_mode == AgentMode.PLAN
        else f"[{mode_color}]Build[/{mode_color}]"
    )

    console.print(
        Panel.fit(
            f"{profile_header}"
            f"[bold blue]Beep.AI.Code[/bold blue]\n"
            f"Workspace: [cyan]{session._workspace.name}[/cyan]"
            f"{memory_info}{git_info}{pin_info}{coding_info}{plugin_info}{skill_info}{rule_info}\n"
            f"Model: {model_display} | AI: [cyan]{session._mode}[/cyan] | Agent: {mode_display} | "
            f"Session: [dim]{session._session_id}[/dim]",
            border_style="blue",
        )
    )
    console.print("Type [cyan]/help[/cyan] for commands, [cyan]/quit[/cyan] to exit\n")


def build_skill_context(session: ChatSession, user_input: str) -> str:
    if not session._skills_enabled:
        return ""
    matches = session._skill_resolver.resolve(user_input, max_skills=3, budget_chars=3000)
    if not matches:
        return ""
    lines = ["## Active Skills"]
    for match in matches:
        lines.append(f"\n### {match.skill.name}\n{match.skill.body}")
    return "\n".join(lines).strip()
