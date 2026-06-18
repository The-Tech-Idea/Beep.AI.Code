# Watcher, Tasks & Bookmarks

**Status:** Shipped  
**Package:** `beep/watcher/`, `beep/tasks/`, `beep/bookmarks/`

## Purpose

File watching with command callbacks; REPL task list; persistent file bookmarks.

## Code locations

| Module | Role |
|--------|------|
| `watcher/service.py` | Watchdog, debounce, timeout |
| `commands/watch.py` | `beep watch` |
| `tasks/manager.py` | TaskManager |
| `bookmarks/manager.py` | BookmarkManager |
| `chat/session_runtime_state.py` | `/task`, `/watch` persistence |

## User surfaces

- `beep watch`
- REPL `/task`, `/watch`
- Bookmarks via chat commands / manager API

## Current behavior

- Watch callback timeout and exit code reporting (Phase 6)
- Task/watch state survives across REPL commands until `/clear`
- Isolated callback failures in watcher

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| WT-1 | `beep watch --dry-run` | P3 | CLI test |
| WT-2 | Task export/import JSON | P2 | Unit test |
| WT-3 | Bookmark sync to server (optional) | P3 | API design |
| WT-4 | Watch multiple patterns per rule file | P2 | Config test |
