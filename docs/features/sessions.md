# Sessions & Compaction

**Status:** Shipped  
**Package:** `beep/sessions/`

## Purpose

Persist chat and agent history locally; list, export, delete; compact long histories.

## Code locations

| Module | Role |
|--------|------|
| `manager.py` | SessionManager |
| `history_support.py` | JSONL scan, atomic writes |
| `compactor.py`, `memory_watch.py` | Compaction |
| `commands/sessions.py` | CLI |

## User surfaces

- `beep sessions list|export|delete`
- REPL `/sessions`, `/resume`, `/compact`

## Current behavior

- Agent runs persisted to JSONL with terminal meta (Phase 7)
- Automatic compaction on save path
- Export formats: markdown, json

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| SE-1 | Encrypt session store at rest (optional) | P3 | Config flag test |
| SE-2 | Import session from export file | P2 | CLI `sessions import` |
| SE-3 | Server-side session sync when API available | P3 | Integration |
| SE-4 | Session search by keyword | P2 | List filter test |
