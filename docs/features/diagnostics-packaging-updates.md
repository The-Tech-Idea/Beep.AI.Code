# Diagnostics, Packaging & Updates

**Status:** Partial  
**Package:** `beep/commands/diagnostics*.py`, `beep/publishing/`, `beep/commands/self_update.py`

## Purpose

Surface install health, plugin/MCP issues, upgrade paths, and release packaging workflows.

## Code locations

| Module | Role |
|--------|------|
| `commands/diagnostics.py` | `diagnostics`, `doctor` |
| `commands/diagnostics_schema_support.py` | Structured output |
| `commands/self_update.py` | Update workflow |
| `diagnostics/monitor.py` | Monitors |
| `publishing/*` | Build/deploy adapters |
| `system_support.py` | Shared status helpers |

## User surfaces

- `beep diagnostics`, `beep doctor [--fix]`, `beep self-update`

## Current behavior

- Plugin path listing and load errors
- Doctor repair guidance; release dry-runs (Phase 14, 18)
- Shared presentation with REPL `/diagnostics` (Phase 6)

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| DP-1 | Add `.github/workflows/beep-ai-code-ci.yml` | P1 | Green CI |
| DP-2 | `beep doctor --json` for automation | P2 | Schema test |
| DP-3 | Version check against PyPI/GitHub releases | P2 | Mock HTTP |
| DP-4 | Managed runtime disk usage report | P2 | Doctor output |
| DP-5 | SBOM export for releases | P3 | Build artifact |
