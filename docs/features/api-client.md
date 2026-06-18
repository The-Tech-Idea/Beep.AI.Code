# API Client & Streaming

**Status:** Partial  
**Package:** `beep/api/`

## Purpose

Async HTTP transport to Beep.AI.Server: OpenAI-compatible chat, models, embeddings, RAG, Coding Assistant bootstrap, agent bundles, token check.

## Code locations

| Module | Role |
|--------|------|
| `client.py` | `BeepAPIClient`, endpoint methods |
| `client_llm_support.py` | LLM request helpers |
| `client_workspace_support.py` | Workspace/bootstrap helpers |
| `client_agent_bundle_support.py` | Bundle import/export HTTP |
| `payloads.py` | Request body shaping |
| `streaming.py` | SSE parsing, tool-call sentinels |

## User surfaces

- All commands that call the server (`chat`, `ask`, `agent`, `rag`, `status`, …)
- REPL model turns via `ChatSession`

## Current behavior

- Bearer auth on `/v1/*` and `/ai-middleware/api/*`
- Retries on 429/503; configurable timeout; `BeepAPIError` mapping
- Streaming chat completions with tool deltas
- Health: `GET /api/health`; optional `GET /ai-middleware/api/tokens/check`

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| API-1 | OpenAPI-derived client stubs or contract tests against server OpenAPI | P2 | CI contract job |
| API-2 | Request/response redaction in debug logs (`BEEP_LOG_JSON`) | P1 | Log snapshot test |
| API-3 | Connection pooling metrics in `beep diagnostics` | P2 | Diagnostics output |
| API-4 | Automatic server version compatibility warning | P1 | Status command test |
| API-5 | Batch embeddings helper for large index jobs | P3 | Unit test |
| API-6 | Circuit breaker after repeated 5xx | P2 | Simulated failure test |
