# Configuration & Setup

**Status:** Shipped  
**Package:** `beep/config.py`, `beep/setup_wizard.py`, `beep/cli_support.py`

## Purpose

Persist server URL, API token, model defaults, MCP servers, and project binding.

## Code locations

| Module | Role |
|--------|------|
| `config.py` | `BeepConfig`, load/save, env overrides |
| `setup_wizard.py` | `beep setup`, agent provider wizard |
| `cli_support.py` | `config-set`, status rendering |

## User surfaces

- `beep setup`, `beep config`, `beep config-set`
- Environment variables (see README)

## Current behavior

- `~/.beepai/code.json` mode `0600`
- `BEEP_*` env overrides at load time
- Numeric validation for `max_tokens`, `temperature` on config-set
- MCP server list in config schema

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| CF-1 | Optional OS keychain for token (use `keyring` dep) | P2 | Integration test |
| CF-2 | `beep config unset <key>` | P2 | CLI test |
| CF-3 | Config profiles (`--profile work`) | P2 | Multi-file test |
| CF-4 | Validate server URL reachability in setup | P1 | Wizard test |
| CF-5 | Redacted `beep config` output (mask token) | P1 | CLI snapshot |
