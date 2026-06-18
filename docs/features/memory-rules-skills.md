# Memory, Rules & Skills

**Status:** Mature (core shipped in phases 2/3/6; backlog is incremental)  
**Package:** `beep/memory/`, `beep/rules/`, `beep/skills/`

## Purpose

Layer project and user instructions into prompts: `.beep.md`, AGENTS-style rules, declarative skill markdown.

## Code locations

| Module | Role |
|--------|------|
| `memory/loader.py` | `.beep.md`, habits, commands, ignore |
| `rules/loader.py` | AGENTS.md, `.beep/rules`, globs |
| `skills/loader.py`, `resolver.py` | Skill discovery and ranking |
| `runtime/workspace.py` | Merges into system prompt |

## User surfaces

- Automatic injection in chat/agent
- `/skills`, `/skill`, `/rules`, `/memory` (REPL)

## Current behavior

- Skills: keywords/globs, token budget truncation (Phase 2)
- Rules: path-based merge, `/rules` debug listing (Phase 3)
- Memory: `ProjectMemory.to_prompt_section()`

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| MR-1 | Server skills pack sync when stable API exists | P3 | Integration test |
| MR-2 | Skill conflict resolution UI (`/skills rank`) | P2 | REPL test |
| MR-3 | Rules JSON schema export for editors | P3 | Schema file |
| MR-4 | Memory diff on git branch switch | P2 | Unit test |
| MR-5 | Validate frontmatter on load with friendly errors | P1 | Loader tests |
