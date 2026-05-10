# Phase 5 — Chat REPL UX & Slash Commands

**Goal:** The interactive REPL is the primary user surface.
It must feel fast, keyboard-friendly, and self-documenting.
Slash commands must be consistent, discoverable, and well-tested.

---

## Todo Tracker

### Fixes

- [ ] **repl.py — `/agent` dispatches to `run_agent()` but does not propagate workspace-root.**
  `run_agent()` calls `find_workspace_root()` internally, but if the user started `beep` from
  a subdirectory the root may differ from the REPL session's root.
  Fix: `ChatSession` stores `_workspace_root` at construction; pass it into `run_agent()`.

- [ ] **repl.py — `_get_coding_metadata()` calls `build_coding_metadata()` on every turn.**
  The project and session IDs are generated anew if not cached. Ensure
  `_coding_project_id` and `_coding_session_id` are consistently threaded.
  The current code sets them in `_get_coding_metadata` but only persists them if
  the server call succeeds — a race if the user calls `/coding on` without a successful turn.

- [ ] **commands/session.py — `CompactCommand` local fallback keeps only 3 messages.**
  When the server compact endpoint is absent the fallback drops all messages except
  system + last user + last assistant. This is fine for a 3-message history but
  destroys context for a 30-message session.
  Fix: keep the last 6 messages (system + 2 full turns) in the local fallback.

- [ ] **command_registry.py — Command names from `command.name` are the keys,
  but aliases are not registered.** Several commands mention aliases in their
  docstrings but aliases don't work. Fix: add `aliases: list[str]` property to
  `Command` base class and register them in the registry.

- [ ] **stream_renderer.py — Tool-call blocks inside streaming responses are not rendered.**
  When the server returns a streaming response that includes tool_call_start / tool_call_end
  events the renderer skips them silently. For chat-mode tool use this means the user
  sees nothing during tool invocation.
  Fix: render a `[tool: name(args...)]` inline block when a tool-call event is seen.

### Enhancements

- [ ] **commands/system.py — `/status` should display `coding_model_tiers` from `v1_health`.**
  Currently `/status` only shows the generic health dict. Add a "Model Tiers" section
  that lists available coding tiers when the server supports it.

- [ ] **commands/llm_turns.py — Add `/ask` command variant that bypasses conversation history.**
  For quick one-off questions, the user should be able to do `/ask what does X do?`
  without it polluting the ongoing session history.
  Implement: `AskCommand` — sends a single-turn request, prints response, does NOT append
  to `self._messages`.

- [ ] **commands/ — Add `/undo` command.**
  Removes the last user + assistant pair from `self._messages`. Useful when the model
  gave a bad answer and the user wants to re-try with a different phrasing without
  clearing the entire session.

- [ ] **repl.py — No keyboard shortcut to cancel a streaming response.**
  Ctrl-C during streaming raises `KeyboardInterrupt` but leaves the session in a state
  where the incomplete response is not appended, so the conversation is inconsistent.
  Fix: catch `KeyboardInterrupt` in the streaming loop, append a truncated assistant
  message `"[cancelled by user]"`, and continue the REPL cleanly.

- [ ] **commands/watch.py — `/watch` exists but is not documented in `/help`.**
  Audit all command `description` strings and ensure they are present.

---

## Acceptance Criteria

1. `/agent` always uses the same workspace root as the active REPL session.
2. `/compact` local fallback keeps last 6 messages.
3. Command aliases work (e.g. `/c` for `/clear`).
4. `/status` shows model tiers when available.
5. `/undo` removes last exchange without touching older history.
6. Ctrl-C during streaming exits cleanly with consistent conversation state.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/chat/repl.py` | 🔧 workspace_root threading; Ctrl-C |
| `beep/chat/command_registry.py` | 🔧 Aliases support |
| `beep/chat/stream_renderer.py` | 🔧 Tool-call event rendering |
| `beep/chat/commands/session.py` | 🔧 Compact fallback |
| `beep/chat/commands/system.py` | 🔧 /status model tiers |
| `beep/chat/commands/llm_turns.py` | 🆕 /ask one-shot variant |
| `beep/chat/commands/session.py` | 🆕 /undo command |
| `tests/test_chat_session_commands.py` | 🔧 Extend |
| `tests/test_chat_misc_commands.py` | 🔧 Extend |
