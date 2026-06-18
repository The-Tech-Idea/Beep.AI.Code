# Workspace & Editing

**Status:** Shipped  
**Package:** `beep/workspace/`, `beep/editing/`

## Purpose

Shared workspace operations for CLI, REPL, and agent tools: tree, cat, grep, search/replace, edit transactions, undo.

## Code locations

| Module | Role |
|--------|------|
| `workspace/detector.py` | Git/workspace root |
| `workspace/ignore.py` | Ignore patterns + `.beep/ignore` |
| `workspace/search.py` | Regex scan (shared) |
| `workspace/view.py` | cat/tree rendering |
| `workspace/editing.py` | Edit prep, undo payloads |
| `workspace/search_replace.py` | Patch application |
| `editing/transaction.py`, `patch.py` | Transactions |
| `commands/workspace.py`, `edit.py` | CLI |

## User surfaces

- `beep tree`, `cat`, `grep`, `edit`
- REPL `/tree`, `/cat`, `/grep`, edit flows
- Agent tools: read, write, search, etc.

## Current behavior

- Centralized search/view/editing (Phase 6 P6-44–46)
- Syntax highlighting via Pygments in `cat`
- Rollback via `AppService.rollback`

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| WS-1 | Binary file detection with explicit skip message | P2 | Unit test |
| WS-2 | Large file guard (size threshold) for cat/agent read | P1 | Test with fixture |
| WS-3 | Unified diff export for `beep edit` | P2 | CLI test |
| WS-4 | `.beepignore` glob syntax doc + validator | P3 | Docs + test |
| WS-5 | WSL path normalization on Windows | P1 | Windows CI test |
