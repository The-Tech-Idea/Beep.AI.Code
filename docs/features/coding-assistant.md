# Coding Assistant Bridge

**Status:** Partial  
**Package:** `beep/coding/`

## Purpose

Attach **Coding Assistant** metadata to chat/agent requests so Beep.AI.Server can link workspace, project, and session the same way as the web assistant.

## Code locations

| Module | Role |
|--------|------|
| `prompt_context.py` | Workspace prompt sections |
| `beep/chat/coding_bridge.py` | Bootstrap from REPL |
| `beep/chat/repl.py` | Coding IDs, approvals hooks |
| `beep/agent/*` | Agent metadata merge |

## User surfaces

- `beep chat` / default REPL (auto-bootstrap)
- `beep agent` (metadata on completions)
- Slash: `/coding on|off`, approval flows

## Current behavior

- `POST /ai-middleware/api/coding-assistant/workspaces/bootstrap` from workspace root
- Optional `project_id` from config / `BEEP_PROJECT_ID`
- Session compaction API when available; local fallback in `/compact`
- Coding metadata includes `workspace_root`, `interaction_mode`

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| CA-1 | E2E test suite against dev server (optional marker) | P1 | pytest marker `server` |
| CA-2 | Surface pending server approvals in TUI (parity with REPL) | P2 | TUI test |
| CA-3 | Document approval UX in user docs with screenshots | P3 | Docs review |
| CA-4 | Retry bootstrap on transient 503 with backoff | P2 | Mock server test |
| CA-5 | `beep coding status` CLI for project/session IDs | P2 | CLI smoke test |
