# Agent Runtime (LangGraph)

**Status:** Partial  
**Package:** `beep/agent/`

## Purpose

Autonomous multi-step coding agent: tool loop, approvals, LangGraph graph, provider packs, subagents, structured output, portable bundles.

## Code locations

| Area | Path |
|------|------|
| Graph | `graph.py`, `graph_runner*.py`, `graph_streaming.py` |
| Loop (legacy/bridge) | `loop.py` |
| Tools | `agent/tools/*`, `tools/factory.py` |
| Providers | `provider_*.py`, `provider_plugins.py` |
| Subagents | `subagents/` |
| Planning | `planning/`, `tools/todo_tool.py` |
| Verification | `verification/` |
| Bundles | `bundle_contract.py`, `bundle_store.py` |
| Commands | `beep/commands/agent*.py` |

## User surfaces

- `beep agent "<goal>"` and agent admin subcommands
- REPL `/agent`
- Provider setup: `beep agent setup`, `providers`, `configure`

## Current behavior

- LangGraph runtime with streaming events (Phase 11, 15)
- Sandbox modes: read-only, workspace-write, full-trust
- Parallel tools, todo list, dispatch_agent subagents, auto-verify hooks
- Multimodal and structured output CLI flags (Phase 16)
- Portable bundle import/export/deploy (Phase 17–18)

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| AG-1 | Coordinated multi-agent blackboard (shared state across workers) | P2 | Design doc + integration test |
| AG-2 | Concurrent agent workers with resource limits | P2 | Stress test |
| AG-3 | Agent run replay from JSONL in `beep agent resume` | P1 | Fixture replay test |
| AG-4 | Cost/token budget per run with hard stop | P1 | Agent test |
| AG-5 | Tool result cache for idempotent reads | P2 | Unit test |
| AG-6 | Offline mode: local tools only with clear banner | P3 | CLI test |
| AG-7 | Graph visualization export (`--graph-dot`) | P3 | Smoke test |
