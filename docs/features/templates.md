# Templates

**Status:** Shipped  
**Package:** `beep/templates/`

## Purpose

Generate files from builtin, user, and workspace templates; language-specific project scaffolds via plugins.

## Code locations

| Module | Role |
|--------|------|
| `catalog.py`, `discovery.py`, `rendering.py` | Domain split (Phase 4) |
| `service.py` | Shared list/generate |
| `generator.py` | Thin facade |
| `plugins/*` | Language scaffolds |
| `commands/template.py` | CLI |

## User surfaces

- `beep template list`, `beep template generate`
- REPL template commands (`system.py`)

## Current behavior

- Paths: builtin, `~/.beepai/templates`, `.beep/templates`
- Variable prompts for missing keys
- `ProjectTemplateRegistry` on AppService

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| TP-1 | Server template fetch + cache (Phase 4 P4-3) | P2 | Mock API test |
| TP-2 | Template preview before write | P2 | CLI test |
| TP-3 | `beep template validate` | P2 | Validator test |
| TP-4 | Template marketplace index file | P3 | Doc only |
