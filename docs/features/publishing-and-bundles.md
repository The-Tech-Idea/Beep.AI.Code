# Publishing & Agent Bundles

**Status:** Shipped  
**Package:** `beep/publishing/`, `beep/agent/bundle_*.py`

## Purpose

Export/import portable agent bundles; package for npm/Python/GitHub/container channels; deploy to Beep.AI.Server.

## Code locations

| Module | Role |
|--------|------|
| `agent/bundle_contract.py` | Manifest schema |
| `agent/bundle_store.py` | Local store |
| `commands/agent_bundle.py` | export/import/run |
| `commands/agent_deploy.py`, `agent_package.py` | Deploy/package |
| `publishing/channel_adapters.py` | Channel wrappers |
| `publishing/release_metadata.py` | Provenance |
| `api/client_agent_bundle_support.py` | Server interop |

## User surfaces

- `beep agent export|import|deploy|package|run`

## Current behavior

- Validation, compatibility tests, provenance placeholders (Phase 17–18)
- Server token-auth bundle endpoints when server supports them

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| PB-1 | Bundle signing required mode | P2 | Contract test |
| PB-2 | `beep agent bundle verify` | P1 | CLI test |
| PB-3 | Changelog embedded in bundle manifest | P3 | Schema bump |
| PB-4 | JS SDK publish automation doc link | P2 | Cross-repo doc |
