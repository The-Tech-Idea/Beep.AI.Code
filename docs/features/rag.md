# RAG

**Status:** Partial  
**Package:** `beep/rag/`, `beep/commands/rag.py`

## Purpose

Query Beep.AI.Server RAG collections from the CLI using token auth.

## Code locations

| Module | Role |
|--------|------|
| `rag/search.py` | Local helpers |
| `api/client.py` | `POST /v1/rag/query`, `GET /v1/rag/collections` |
| `commands/rag.py` | CLI |

## User surfaces

- `beep rag query`, `beep rag collections`
- REPL `/rag`

## Current behavior

- Requires `rag:read` scope
- Displays collections and query results in terminal

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| RAG-1 | Interactive collection picker | P2 | CLI test |
| RAG-2 | Citation formatting with source paths | P1 | Output snapshot |
| RAG-3 | RAG result inject into chat context (`/rag use`) | P2 | REPL test |
| RAG-4 | Filter by collection id in query flags | P2 | CLI test |
