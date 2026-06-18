# Beep.AI.Server Integration (Default Backend)

**Status:** Partial — **Slices 1-4 shipped, 5-7 blocked on server access**  
**ID prefix:** `SRV`  
**Implementation plan:** [.plans/PHASE_23_SERVER_INTEGRATION_PARITY.md](../../.plans/PHASE_23_SERVER_INTEGRATION_PARITY.md)

## Principle

Beep.AI.Code's **default backend is Beep.AI.Server** (default `server_url = http://localhost:5000`, `beep` provider pack), while remaining provider-agnostic (OpenAI/Anthropic/OpenRouter/local). This plan makes the CLI track the **current** server contract and progressively use **all relevant server features**.

Server source of truth: `Beep.AI.Server/Beep.AI.Server/docs/INDEX.md` and `docs/ai-services/`.

## CRITICAL drift (P0)

The server INDEX states: *"The old `ai_middleware` namespace has been renamed to `v1`… only V1 APIs (`/v1/api/*`) and all local OpenAI-compatible `/v1/*` APIs use application tokens."* Verified: `tokens/check` is now `/v1/api/tokens/check` (`app/routes/v1/tokens.py`).

The CLI still calls **legacy `/ai-middleware/api/*` paths** in [`beep/api/client.py`](../../beep/api/client.py):

| CLI call (current) | Likely current server path | Status |
|--------------------|----------------------------|--------|
| `/ai-middleware/api/tokens/check` | `/v1/api/tokens/check` | **Confirmed renamed** |
| `/ai-middleware/api/coding-assistant/workspaces/bootstrap` | unified into `/v1/chat/completions` coding metadata + `coding_session_service` (no standalone bootstrap route found) | **Likely removed/renamed** |
| `/ai-middleware/api/coding-assistant/projects/{id}/bootstrap` | same as above | **Verify** |
| `/ai-middleware/api/coding-assistant/projects/{id}/sessions` | same as above | **Verify** |
| `/ai-middleware/api/coding-assistant/sessions/compact` | `/v1/api/...` or chat-path compaction | **Verify** |
| `/ai-middleware/api/agents/bundles/import` | `/v1/...` agent bundles (`app/routes/v1/agent_bundles.py`) | **Likely renamed** |

The server also notes: *"Single chat execution path on local OpenAI `/v1/chat/completions`; legacy middleware chat endpoints are removed from active use."* — so coding-session linkage should flow through chat-completions metadata, not a separate bootstrap endpoint.

## Server feature → CLI usage matrix

Server services (16) from `docs/ai-services/INDEX.md` and route catalog. "Relevance" = value to a terminal coding agent.

| Server service | API prefix | CLI today | Relevance | Gap / action (SRV) |
|----------------|-----------|-----------|-----------|---------------------|
| LLM (chat/models/embeddings/responses/messages) | `/v1` | ✓ used | High | Keep; align responses/messages usage (SRV-3) |
| RAG | `/v1/rag` | partial (query, collections) | High | Add ingest, chunk templates, metadata filters, tenancy headers, graph RAG (SRV-4) |
| RAG Cluster | `/api/rag/cluster/*` | ✗ | Low-Med | Status read-only surfacing (SRV-12) |
| Agents (hosted) | `/v1` agent routes, `agent_operations` | ✗ (local LangGraph) | Med | Optional: run/list server-hosted agents (SRV-6) |
| Agent bundles | `/v1` `agent_bundles` | partial (import) | High | Fix path; full export/deploy parity (SRV-2) |
| Agent Studio (workflows) | `/studio` | ✗ | Med | Trigger/list studio workflows from CLI (SRV-9) |
| MCP | `/v1/mcp`, `/mcp/registry` | own presets only | High | Consume server MCP registry/catalog (SRV-5) |
| Tooling | `/v1/tooling` | ✗ | Med | Discover/execute server tools as agent tools (SRV-7) |
| Audio (STT/TTS/V2V) | `/audio`, `/v1` playground | ✗ | Med | Voice input/output for chat (SRV-10) |
| Vision | `/vision` | local multimodal only | Med | Route image understanding to server vision (SRV-8) |
| Document Extraction | `/document-extraction` | ✗ | Med | Extract docs → context/RAG (SRV-8) |
| Text-to-Image | `/text-to-image` | ✗ | Low | Defer |
| Object Detection | via vision | ✗ | Low | Defer |
| ML Models | `/ml-models`, `/api/v1/ml-models` | ✗ | Low | Defer |
| Personal Assistant | PA blueprint | ✗ | Low | Defer |
| Workflow Engine | `/workflow-engine` | ✗ | Low-Med | Defer / trigger-only |
| Job Scheduler | `/job-scheduler`, `/v1` scheduler_jobs | ✗ | Med | Scheduled agent runs (ties NF-9) (SRV-11) |
| Service calls (+ multimodal) | `/v1` `service_calls*` | ✗ | Med | Generic service invocation + chaining (SRV-13) |
| Middleware rules/policies/ops | `/v1/api` | ✗ | Low | Operator-only; defer |
| Capability discovery | `/v1` services list | ✗ | High | `beep` discovers enabled services + scopes (SRV-1) |

## Enhancement backlog

| ID | Item | Priority | Verification |
|----|------|----------|----------------|
| SRV-1 | **Capability discovery**: on connect, query the server's service/capability list + token scopes; gate CLI features to what the server actually exposes; show in `beep status`/`diagnostics` | P0 | Mock server catalog test |
| SRV-2 | **Namespace migration**: move all `/ai-middleware/api/*` calls to `/v1/api/*`; fix bundles import path; verify each against running server | P0 | Path tests vs server fixtures |
| SRV-3 | **Coding-session via chat path**: replace standalone bootstrap with `/v1/chat/completions` coding metadata + `coding_session_service` contract; keep `project_id`/`session_id` linkage | P0 | Coding linkage integration test |
| SRV-4 | **RAG parity**: ingest, chunk templates, metadata filters, application tenancy headers, graph RAG query | P1 | RAG contract tests |
| SRV-5 | **Server MCP registry**: consume `/v1/mcp` + `/mcp/registry` so server-managed MCP servers appear in the CLI catalog (ties INT-2/PH-20) | P1 | Registry fetch test |
| SRV-6 | **Hosted agents (optional)**: list/run server-side agent definitions as an alternative to local LangGraph | P2 | Mock run test |
| SRV-7 | **Server tooling**: expose `/v1/tooling` tools to the agent tool layer | P2 | Tool mapping test |
| SRV-8 | **Vision + document extraction**: route image/doc understanding to server services, feeding context | P2 | Service-call tests |
| SRV-9 | **Agent Studio triggers**: list/trigger studio workflows from CLI | P2 | Trigger test |
| SRV-10 | **Audio**: STT for voice input, TTS for spoken output in chat/TUI | P3 | Playground STT test |
| SRV-11 | **Scheduler**: submit scheduled agent runs via `/v1` scheduler jobs (ties NF-9/CAP) | P2 | Job submit test |
| SRV-12 | **RAG cluster status** read-only surface in diagnostics | P3 | Status read test |
| SRV-13 | **Generic service calls**: support `/v1` service_calls (+ multimodal) for chaining | P3 | Chaining test |
| SRV-14 | **Default-backend UX**: make Beep.AI.Server the explicit default with one-step `beep setup`; clear messaging when pointed at a non-Beep provider (feature degradation map) | P1 | Setup + status tests |
| SRV-15 | **Version/compat handshake**: read server version + feature flags; warn on incompatible client (ties API-4) | P1 | Handshake test |

## Default vs other providers

- **Default:** Beep.AI.Server. `config.server_url` defaults to `http://localhost:5000`; the `beep` provider pack is primary; Beep-specific features (coding sessions, RAG tenancy, MCP registry, tooling) activate only against Beep.AI.Server.
- **Other providers:** OpenAI/Anthropic/OpenRouter/local stay supported for raw `/v1` chat; Beep-only features are **gracefully disabled** with a clear capability map (SRV-1, SRV-14).

Return to [../ENHANCEMENT_PLAN.md](../ENHANCEMENT_PLAN.md) · [api-client.md](api-client.md) · [coding-assistant.md](coding-assistant.md)
