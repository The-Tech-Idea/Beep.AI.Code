# Phase 4 — Context Management & Prompt Quality

**Goal:** Every LLM call — agent and chat — must be backed by the right
system prompt, the right workspace context, and a context window that stays
within budget. Prompts must be self-consistent: they must tell the LLM
what tools it has and how to use them.

---

## Todo Tracker

### Fixes

- [ ] **prompts.py — Static `CODE_ASSISTANT` prompt has no tool-awareness section.**
  The agent uses this prompt but never tells the LLM what tools are available,
  their names, when to use each, or the "read-before-edit" pattern.
  Fix: add a `### Available Tools` section rendered dynamically by
  `build_workspace_system_prompt()` using the tool definitions from `factory.py`.

- [ ] **prompts.py — No distinct `agent` mode.**
  `get_system_prompt()` has only `"assistant"`, `"review"`, and `"explain"` modes.
  The agent loop always uses `"assistant"`. A purpose-built agent prompt is needed that:
  - Specifies the available tools and when to call them.
  - Requires reading a file before editing it.
  - Requires confirming understanding of a large codebase before making changes.
  - Discourages verbose "I will now..." preambles.
  Fix: add `"agent"` mode to `get_system_prompt()` with an agent-optimised prompt.

- [ ] **coding/prompt_context.py — `build_workspace_system_prompt("agent", ...)` not called.**
  `run_agent()` uses `get_system_prompt("assistant")` directly, bypassing
  `build_workspace_system_prompt` which injects memory, rules, and project context.
  Fix: `run_agent()` must call `build_workspace_system_prompt("agent", ...)` and pass the
  result as the system message.

- [ ] **context/window.py — `truncate_messages` keeps the last N messages by token budget,
  but it starts from the end and inserts to front — this reversal can corrupt pairs.**
  A `user` message with its following `assistant` reply must stay together.
  Fix: truncate from oldest pairs, not from oldest individual messages.
  Ensure `tool_calls` message and all corresponding `tool` response messages are always
  kept together (they form a single logical unit).

- [ ] **context/builder.py — `MAX_CONTEXT_FILES = 10` hard limit drops context silently.**
  If 11 files are @-mentioned the 11th is silently omitted.
  Fix: emit a warning comment in the context block listing omitted files.

- [ ] **context/window.py — Token estimate uses 0.25 chars/token.**
  This is inaccurate for code (code tokenizes ~1.2 chars/token on average for GPT-4).
  Fix: use 0.35 as a safer default and document it as an approximation.

### Enhancements

- [ ] **coding/prompt_context.py — Inject active tool list into system prompt.**
  After building rules + memory context, append a `### Tools Available` block that
  lists each tool's name and a one-line description. This removes the LLM's need to
  hallucinate tool names.

- [ ] **context/smart.py — Implement smart context selection.**
  `smart.py` likely exists but may be a stub. Implement `select_context_files()`:
  given the user query, use fuzzy search + extension filtering to rank the most
  relevant files in the workspace and return up to `MAX_CONTEXT_FILES` paths.
  This replaces the current "all @-mentioned" approach with an automatic one.

- [ ] **coding/metadata.py — `build_coding_metadata()` does not include workspace root.**
  The server uses `coding_assistant.workspace_root` to resolve file paths.
  Ensure `workspace_root` is always included and is the resolved absolute path.

- [ ] **context/builder.py — Add `build_context_from_symbols(query, workspace_root)` function.**
  Runs `search` (grep) for the query across the workspace and builds context from
  matching files. Used by the agent when it needs semantic-nearest code without browsing.

---

## Acceptance Criteria

1. `get_system_prompt("agent")` returns a prompt with a tools section.
2. `run_agent()` uses `build_workspace_system_prompt("agent", ...)`.
3. `truncate_messages` keeps paired messages together.
4. Context injection in chat correctly warns when files are omitted.
5. `smart.py` `select_context_files()` returns ranked file paths based on a query.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/chat/prompts.py` | 🔧 Add agent mode |
| `beep/coding/prompt_context.py` | 🔧 Inject tool list |
| `beep/coding/metadata.py` | 🔧 Ensure workspace_root |
| `beep/context/builder.py` | 🔧 Add omit warning + symbol search |
| `beep/context/window.py` | 🔧 Pair-safe truncation + better token ratio |
| `beep/context/smart.py` | 🆕 Implement |
| `beep/agent/loop.py` | 🔧 Call build_workspace_system_prompt |
