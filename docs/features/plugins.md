# Plugins

**Status:** Mature (core shipped in phase 1; backlog is incremental)  
**Package:** `beep/plugins/`

## Purpose

Extend REPL and agent with user/workspace Python plugins: extra tools, slash commands, context snippets.

## Code locations

| Module | Role |
|--------|------|
| `registry.py`, `registry_support.py` | Discovery, registration |
| `runtime.py` | Load and wire into session |
| `commands/plugins.py` | `beep plugins paths`, `add-path` |

## User surfaces

- `beep chat --no-plugins`, `beep agent --no-plugins`
- `/plugins` in REPL
- `beep plugins` command group

## Current behavior

- Discovery: `~/.beepai/plugins`, `.beep/plugins`, `BEEP_PLUGINS_DIR`
- In-process execution (trusted code)
- Agent appends `registry.get_tools()` in factory

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| PL-1 | Plugin manifest (`plugin.json`) with version constraints | P2 | Schema test |
| PL-2 | Optional subprocess sandbox for untrusted plugins | P2 | Design + spike |
| PL-3 | `beep plugins doctor` as top-level alias | P3 | CLI test |
| PL-4 | Hot reload on file change (dev mode) | P3 | Manual |
| PL-5 | Plugin signing / allowlist | P3 | Security doc |
