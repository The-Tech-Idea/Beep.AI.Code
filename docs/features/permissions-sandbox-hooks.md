# Permissions, Sandbox & Hooks

**Status:** Mature (core shipped in phase 13; backlog is incremental)  
**Package:** `beep/permissions/`, `beep/sandbox/`, `beep/hooks/`, `beep/security/`

## Purpose

Control tool execution risk: approval prompts, sandbox modes, shell hooks around lifecycle events.

## Code locations

| Module | Role |
|--------|------|
| `permissions/manager.py` | `PermissionManager`, `SandboxMode` |
| `agent/approval.py` | Agent approval flow |
| `hooks/manager.py` | `~/.beepai/hooks.json` |
| `validation/policy.py` | Policy checks |

## User surfaces

- `beep agent --sandbox`, `-y`
- REPL `/hooks`
- Hook events on tool start/end (extensible)

## Current behavior

- Sandbox: read-only, workspace-write, full-trust
- Auto-approve with `-y` (documented security risk)
- Hooks loaded at startup via AppService

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| PS-1 | Per-tool permission profiles in config | P1 | Config schema test |
| PS-2 | Audit log file for approved/denied tools | P2 | Log format test |
| PS-3 | Hook schema validation on load | P1 | hooks.json test |
| PS-4 | macOS/Linux sandbox integration (landlock/firejail optional) | P3 | Spike |
| PS-5 | Document sandbox matrix in user docs | P1 | Docs review |
