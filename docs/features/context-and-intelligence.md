# Context & Workspace Intelligence

**Status:** Partial  
**Package:** `beep/context/`, `beep/runtime/builtin_workspace_intelligence.py`

## Purpose

Select and inject relevant files into prompts; language-aware intelligence (Python Jedi, Semble semantic search, tree-sitter).

## Code locations

| Module | Role |
|--------|------|
| `context/smart.py` | `SmartContextBuilder` |
| `context/auto_context.py` | `AutoContextBuilder` + Semble |
| `context/builder.py`, `window.py` | Context assembly |
| `agent/tools/semantic_search.py` | Semble tools |
| `agent/tools/python_intelligence*.py` | Jedi tools |
| `runtime/builtin_workspace_intelligence.py` | Plugin wiring |

## User surfaces

- Automatic context in chat/agent system prompts
- Agent tools: semantic search, Python intelligence
- Optional `semble` extra in `pyproject.toml`

## Current behavior

- `SmartContextBuilder.select_context_files()` for agent/chat
- Per-workspace `semble_index`, `python_jedi` via AppService
- Semble MCP preset when MCP enabled

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| CX-1 | Token budget dashboard in `/status` | P2 | REPL test |
| CX-2 | Incremental Semble index on file save (watcher hook) | P1 | Integration test |
| CX-3 | Cross-language LSP bridge (generic LSP client) | P2 | Spike + doc |
| CX-4 | Context explain: `/context why` shows ranked files | P2 | Command test |
| CX-5 | Cache invalidation when branch changes (git) | P2 | Unit test |
