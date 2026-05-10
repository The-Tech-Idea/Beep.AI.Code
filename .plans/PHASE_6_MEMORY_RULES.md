# Phase 6 — Memory, Rules, and Skills

**Goal:** Every agent/chat run should be enriched by persistent memory,
project-specific rules, and reusable skills. Currently these subsystems
are loaded but not consistently injected into the agent flow.

---

## Todo Tracker

### Fixes

- [ ] **memory/loader.py — `lru_cache` on `get_workspace_runtime()` means memory is stale.**
  After the user edits `.beep.md` or `.beep/habits.md`, the running `beep` session
  sees the old content until restarted.
  Fix: add a `/memory reload` slash command that clears `get_workspace_runtime.cache_clear()`
  and reloads the runtime for the current workspace.

- [ ] **loop.py — Agent system prompt does not include `ProjectMemory`.**
  The chat REPL injects memory via `build_workspace_system_prompt`, but `run_agent()`
  uses `get_system_prompt("assistant")` (static). Project habits, coding rules, and
  custom commands are invisible to the agent.
  Fix: this is a duplicate of the Phase 4 item — resolve in Phase 4; note here.

- [ ] **memory/loader.py — `.beep/commands.md` is loaded but never surfaced to the user.**
  Custom slash commands defined in the memory file are not registered in
  `command_registry.py`. The user has no way to know their commands are ignored.
  Fix: after loading `ProjectMemory`, check `memory.commands` and register them
  as dynamic `CustomCommand` objects that send the command text as a user message.

- [ ] **rules/resolver.py — `resolve_rules_for_path` only matches a single target path.**
  The agent may be editing multiple files in one session; rules for `src/**/*.py` should
  apply even if the agent hasn't explicitly set a target path.
  Fix: `AgentSession` tracks the set of `_files_touched`; at each step, union the rules
  applicable to any touched file and inject them into the running system prompt.

### Enhancements

- [ ] **memory/ — Add `ProjectMemory.to_prompt_section()` method.**
  Returns a Markdown section string of all loaded memory sub-sections with headers.
  Called by `build_workspace_system_prompt()` instead of manually concatenating fields.

- [ ] **skills/ — Skills are loaded by `WorkspaceRuntime` but never used in agent prompts.**
  Skills are structured reusable instructions (e.g. "how to write a unit test for this
  codebase"). Inject them as optional prompt sections in `build_workspace_system_prompt`
  when a relevant skill matches the user query via keyword similarity.

- [ ] **memory/ — Add `AgentMemory` class for within-session memory.**
  Different from `ProjectMemory`. Stores facts the agent discovers during a run
  (e.g. "the test runner is pytest", "the app entry point is src/main.py").
  Written to a scratch `.beep/session_memory.json` and cleared on new session.

- [ ] **memory/loader.py — Support `.beep/ignore` for exclusions.**
  `.beep/ignore` is mentioned in the architecture but `IgnoreMatcher` loads
  `.beepignore` or `.gitignore`. Unify: if `.beep/ignore` exists, treat it as
  `.beepignore` as well.

---

## Acceptance Criteria

1. `/memory reload` clears and reloads workspace runtime.
2. Custom commands from `.beep/commands.md` are registered as slash commands.
3. Agent system prompt includes `ProjectMemory` sections.
4. `ProjectMemory.to_prompt_section()` exists and is used.
5. Skills matching the user query are injected into the agent system prompt.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/memory/loader.py` | 🔧 to_prompt_section + custom command support |
| `beep/runtime/workspace.py` | 🔧 Expose cache_clear |
| `beep/chat/commands/` | 🆕 /memory reload command |
| `beep/rules/resolver.py` | 🔧 Multi-file rules union |
| `beep/agent/loop.py` | 🔧 Thread memory into agent prompt (Phase 4) |
| `beep/skills/` | 🔧 Skill injection into prompts |
| `beep/workspace/ignore.py` | 🔧 Support .beep/ignore |
