"""Interactive chat REPL — Claude Code style.

Uses command registry for all slash commands.
Supports @file mentions, pinned files, multi-line input.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


from beep.api.client import BeepAPIClient
from beep.chat.coding_bridge import bootstrap_coding_workspace
from beep.chat.command_registry import build_custom_command_registry
from beep.chat.commands.llm_turns import stream_assistant_turn
from beep.chat.context import ChatContext
from beep.chat.input import read_multiline
from beep.chat import repl_context_support, repl_runtime_support
from beep.coding.metadata import build_coding_metadata
from beep.coding.response_metadata import count_pending_approvals, find_coding_identity
from beep.permissions.manager import SandboxMode
from beep.plugins.runtime import PluginRuntime
from beep.rules.resolver import build_rules_context
from beep.runtime.workspace import get_workspace_runtime
from beep.sessions.history import (
    create_session_id,
    maybe_compact_session,
    replace_session,
    save_message,
)
from beep.sessions.memory_watch import MemoryWatcher
from beep.skills.resolver import SkillResolver
from beep.utils.json_logging import log_event
from beep.workspace.detector import find_workspace_root
from beep.workspace.git import get_git_status, is_git_repo


from beep.utils.console import get_console


class ChatSession:
    """Manages a chat conversation session."""

    def __init__(
        self,
        client: BeepAPIClient,
        *,
        model: str | None = None,
        mode: str = "assistant",
        show_tokens: bool = False,
        plugins_enabled: bool = True,
        session_id: str | None = None,
        config: Any = None,
    ) -> None:
        self._client = client
        self._model = model
        self._mode = mode
        self._show_tokens = show_tokens
        self._session_id = session_id or create_session_id()
        self._config = config
        self._messages: list[dict[str, str]] = []
        self._edit_target: Path | None = None
        self._token_count: int = 0
        self._request_count: int = 0
        self._last_edit: dict[str, Any] | None = None
        self._last_output: str = ""
        self._task_manager: Any = None
        self._watcher: Any = None
        self._mcp_runtime_state: Any = None
        self._hook_config = None
        self._sandbox_mode: SandboxMode = SandboxMode.WORKSPACE_WRITE
        self._sandbox: bool = False
        self._max_token_budget: int | None = None
        runtime = get_workspace_runtime(find_workspace_root(), plugins_enabled=plugins_enabled)
        self._workspace = runtime.workspace
        self._memory = runtime.memory
        from beep.app_service import get_app_service

        self._context = get_app_service().chat_context(self._workspace)
        # Merge built-in commands with project-defined custom commands
        custom_commands = build_custom_command_registry(runtime.memory.commands)
        self._commands = {**runtime.commands, **custom_commands}
        self._plugins_enabled = plugins_enabled
        self._plugin_runtime: PluginRuntime = runtime.plugin_runtime
        self._plugin_commands = runtime.plugin_commands
        self._rules, self._rule_errors = runtime.rules, runtime.rule_errors
        self._skills = runtime.skills
        self._skill_errors, self._skill_roots = runtime.skill_errors, runtime.skill_roots
        self._skill_resolver = SkillResolver(self._skills)
        self._skills_enabled = True
        self._auto_context_enabled = True
        self._semantic_search_adapter = runtime.semantic_search_adapter
        self._coding_project_id: int | None = None
        self._coding_session_id: str | None = None
        self._coding_enabled: bool = True
        # Memory management
        self._auto_compact: bool = True
        self._memory_watcher: MemoryWatcher = MemoryWatcher()
        self._messages = [{"role": "system", "content": self._build_system_prompt_content(mode)}]

    def _build_system_prompt_content(self, mode: str) -> str:
        """Build system prompt with project memory and plugin context."""
        return repl_context_support.build_system_prompt_content(self, mode)

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def coding_project_id(self) -> int | None:
        return self._coding_project_id

    @property
    def coding_session_id(self) -> str | None:
        return self._coding_session_id

    @property
    def coding_enabled(self) -> bool:
        return self._coding_enabled

    @property
    def plugins_enabled(self) -> bool:
        return self._plugins_enabled

    def set_coding_enabled(self, enabled: bool) -> None:
        self._coding_enabled = enabled

    @property
    def auto_context_enabled(self) -> bool:
        return self._auto_context_enabled

    def set_auto_context_enabled(self, enabled: bool) -> None:
        self._auto_context_enabled = enabled

    @property
    def semantic_search_adapter(self) -> object | None:
        return self._semantic_search_adapter

    def _get_coding_metadata(self) -> dict[str, Any] | None:
        """Get coding_assistant metadata for chat requests."""
        if not self._coding_enabled:
            return None
        if self._coding_project_id:
            return build_coding_metadata(
                workspace_root=self._workspace,
                interaction_mode="inline",
                project_id=self._coding_project_id,
                session_id=self._coding_session_id,
            )
        configured_project_id = getattr(self._config, "project_id", None)
        return build_coding_metadata(
            workspace_root=self._workspace,
            interaction_mode="inline",
            project_id=configured_project_id,
        )

    async def _bootstrap_workspace(self) -> None:
        """Resolve workspace with server and get project/session IDs."""
        await repl_runtime_support.bootstrap_workspace(
            self,
            console=get_console(),
            log_event=log_event,
            bootstrap_coding_workspace=bootstrap_coding_workspace,
        )
        # Fetch server skills and merge with local skills
        await self._load_server_skills()

    async def _load_server_skills(self) -> None:
        """Fetch global skills from the server and merge with local skills."""
        try:
            from beep.api.client_workspace_support import fetch_server_skills
            from beep.skills.loader import server_skills_to_definitions

            server_skills = await fetch_server_skills(self._client)
            if not server_skills:
                return

            remote_defs = server_skills_to_definitions(server_skills)
            # Merge: local skills first, then server skills (dedup by name, local wins)
            local_names = {s.name for s in self._skills}
            for s in remote_defs:
                if s.name not in local_names:
                    self._skills.append(s)
            self._skill_resolver = SkillResolver(self._skills)
        except Exception:
            # Server skills are optional — silently skip if unavailable
            pass

    @property
    def messages(self) -> list[dict[str, str]]:
        return self._messages

    def clear_history(self) -> None:
        self._messages = [self._messages[0]]

    def set_model(self, model: str | None) -> None:
        self._model = model

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._messages[0] = {"role": "system", "content": self._build_system_prompt_content(mode)}

    def _save(self, role: str, content: str) -> None:
        save_message(self._session_id, {"role": role, "content": content})
        compacted = maybe_compact_session(self._session_id, self._messages)
        if compacted is not self._messages:
            self._messages = compacted
            replace_session(self._session_id, self._messages)
            self._memory_watcher.reset()

    def _check_memory_after_turn(self) -> None:
        """Emit an inline memory warning after each assistant turn if needed."""
        from beep.sessions.history import HISTORY_DIR

        session_file = HISTORY_DIR / f"{self._session_id}.jsonl"
        warning = self._memory_watcher.check(self._messages, session_file)
        if warning is not None:
            get_console().print(warning.render())

    def resume_session(self, session_id: str) -> bool:
        from beep.sessions.history import load_session

        return repl_context_support.resume_session(
            self,
            session_id,
            console=get_console(),
            load_session=load_session,
        )

    async def send(self, user_input: str) -> None:
        await repl_runtime_support.send(
            self,
            user_input,
            console=get_console(),
            log_event=log_event,
            stream_assistant_turn=stream_assistant_turn,
            build_rules_context=build_rules_context,
        )

    def _update_coding_ids(self, response: str) -> None:
        """Update project/session IDs from first coding response."""
        repl_runtime_support.update_coding_ids(
            self,
            response,
            log_event=log_event,
            find_coding_identity=find_coding_identity,
        )

    def _handle_coding_approvals(self, response_text: str) -> None:
        """Display pending code changes from server response."""
        repl_runtime_support.handle_coding_approvals(
            self,
            response_text,
            console=get_console(),
            log_event=log_event,
            count_pending_approvals=count_pending_approvals,
        )

    def _show_welcome(self) -> None:
        repl_context_support.show_welcome(
            self,
            console=get_console(),
            is_git_repo=is_git_repo,
            get_git_status=get_git_status,
        )

    async def run(self) -> None:
        await repl_runtime_support.run(
            self,
            console=get_console(),
            read_multiline=read_multiline,
        )

    async def _handle_command(self, command: str) -> None:
        await repl_runtime_support.handle_command(
            self,
            command,
            console=get_console(),
            log_event=log_event,
        )

    def _build_skill_context(self, user_input: str) -> str:
        return repl_context_support.build_skill_context(self, user_input)

    @property
    def hook_config(self):
        if self._hook_config is None:
            from beep.hooks.manager import load_hooks

            self._hook_config = load_hooks()
        return self._hook_config
