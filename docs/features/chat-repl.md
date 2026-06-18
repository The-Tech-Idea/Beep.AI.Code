# Chat REPL & Slash Commands

**Status:** Shipped  
**Package:** `beep/chat/`

## Purpose

Interactive terminal chat: streaming output, slash commands, pinned context, plugin dispatch, session persistence.

## Code locations

| Module | Role |
|--------|------|
| `repl.py` | `ChatSession`, main loop |
| `runner.py` | Entry from `beep chat` |
| `command_registry.py` | Slash command registration |
| `commands/*.py` | Command implementations by concern |
| `commands/llm_turns.py` | Shared model-turn bookkeeping |
| `stream_renderer.py` | Streaming UI |
| `session_runtime_state.py` | Task/watch state on session |

## User surfaces

- `beep`, `beep chat`
- Slash commands (`/help`, `/agent`, …)

## Current behavior

- Plugin slash merge and unknown `/foo` → plugin handler
- Skills/rules/memory injected via `WorkspaceRuntime`
- Token budget guards on AI slash commands
- `/compact`, `/resume`, `/sessions` wired (Phase 5–7)
- Ctrl-C handling during stream

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| CH-1 | Slash command discoverability: grouped `/help` with categories | P2 | Snapshot test |
| CH-2 | REPL multiline input mode (Alt+Enter) | P3 | Manual + test |
| CH-3 | Export current session from `/sessions export` without leaving REPL | P2 | REPL test |
| CH-4 | Voice / audio input hook (optional) | P3 | N/A |
| CH-5 | Per-session model override persistence in session JSON | P2 | Session file test |
| CH-6 | Rate-limit user messages when server returns 429 | P1 | Mock stream test |
