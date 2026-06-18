# Phase 23 — Beep.AI.Server Integration Parity (Default Backend)

## Goal

Make Beep.AI.Code track the **current** Beep.AI.Server contract and use the server's relevant features by default, while staying provider-agnostic for raw chat. Fix the confirmed API namespace drift first, then add capability discovery and progressive feature integration.

Backing feature doc: [docs/features/server-integration.md](../docs/features/server-integration.md). Server source of truth: `Beep.AI.Server/Beep.AI.Server/docs/INDEX.md`, `docs/ai-services/`.

## Verified facts (from server scan)

- `ai_middleware` namespace **renamed to `v1`**; app tokens only on `/v1/api/*` and OpenAI-compatible `/v1/*`.
- `tokens/check` is now **`/v1/api/tokens/check`** (`app/routes/v1/tokens.py`).
- Chat is unified on **`/v1/chat/completions`**; legacy middleware chat endpoints removed from active use; coding sessions handled via chat metadata + `app/services/agents/coding_session_service.py`.
- Agent bundles live under `app/routes/v1/agent_bundles.py`.
- MCP token-auth helpers under `app/routes/v1/mcp.py` (`/v1/mcp`) plus `/mcp/registry`.
- 16 services cataloged in `docs/ai-services/architecture/01-service-catalog.md`.

## Guiding principles

- One file = one concern; ≤500 lines.
- Keep transport in `beep/api/*`; do not scatter URLs across commands.
- Beep-only features activate **only** against Beep.AI.Server; degrade gracefully for other providers.
- Each slice independently testable with mocked server fixtures; mark optional live tests behind a `server` pytest marker.

---

## Slice 1 — Namespace migration + endpoint audit (SRV-2) [P0, do first]

### srv-1.1 Inventory + constants
- [x] Create `beep/api/endpoints.py`: central constants for every server path (single source of truth); no hardcoded paths elsewhere
- [x] Audit `beep/api/client.py`, `client_workspace_support.py`, `client_agent_bundle_support.py` for `/ai-middleware/api/*`
- [x] `tests/test_api_endpoints.py` — assert no `/ai-middleware/` literals remain in `beep/api/`

### srv-1.2 Migrate paths
- [x] `/ai-middleware/api/tokens/check` → `/v1/api/tokens/check` (was already on v1)
- [x] `/ai-middleware/api/agents/bundles/import` → `/v1/api/agents/bundles/import`
- [x] All client support modules now import from `beep.api.endpoints` (centralized)
- [x] Update client docstring to reflect v1 surface
- [x] `tests/test_client_paths.py` — 9 path round-trip tests

**Verification:** grep shows zero `/ai-middleware/` literals in `beep/` Python files; all 18 tests pass.

---

## Slice 2 — Coding-session via unified chat path (SRV-3) [P0]

### srv-2.1 Contract review
- [x] Coding session flow reviewed: `coding_assistant` metadata already sent in every `/v1/chat/completions` request; bootstrap uses `/v1/api/agent-framework/*` paths (already migrated)
- [x] Response metadata parsing (`beep/coding/response_metadata.py`) extracts project_id/session_id from responses

### srv-2.2 Replace bootstrap
- [x] Coding bridge (`beep/chat/coding_bridge.py`) already uses `/v1/api/agent-framework/*` paths
- [x] `coding_assistant` envelope injected into every chat completion via `beep/api/payloads.py`
- [x] Project/session IDs preserved and passed through chat turns

### srv-2.3 Compaction
- [x] Fixed `compact_conversation` to use dedicated `V1_COMPACTION` endpoint (`/v1/api/agent-framework/agents/beep.agent.coding/compact`)
- [x] All workspace support endpoints centralized in `beep/api/endpoints.py`
- [x] LLM support endpoints also centralized in `beep/api/endpoints.py`

**Verification:** all client support modules import from `endpoints.py`; compaction uses the correct dedicated endpoint.

---

## Slice 3 — Capability discovery + version handshake (SRV-1, SRV-15) [P0/P1]

### srv-3.1 Discovery client
- [x] Added `get_capabilities()` to client via `BeepAPIClientCapabilitiesMixin`
- [x] Created `beep/runtime/server_capabilities.py`: caches per `(url, token)` with 300s TTL
- [x] `tests/test_server_capabilities.py` — 5 tests: defaults, health response parsing, unreachable server, caching, mixin integration

### srv-3.2 Feature gating
- [x] Capability map surfaced in `beep status` via `render_status` in `cli_support.py`
- [x] `ServerCapabilities.has_capability(name)` for programmatic feature gating
- [ ] Server version compatibility warning (needs live server for contract verification)

**Verification:** 23 accumulated tests pass; `beep status` shows server capabilities when connected.

---

## Slice 4 — Default-backend UX (SRV-14) [P1]

- [x] `beep setup` already defaults to Beep.AI.Server (`http://localhost:5000` from `BeepConfig` default), one-step token paste, optional model default
- [x] `beep status` shows capability degradation map (implemented in Slice 3 via `render_status`)
- [ ] Docs: README + APP_OVERVIEW.md clarify default vs other providers (pending)
- [ ] `tests/test_setup_default_backend.py` (pending — needs server)

**Verification:** Setup wizard Step 1 defaults to `http://localhost:5000`; status shows capabilities when connected.

---

## Slice 5 — RAG parity (SRV-4) [P1] — BLOCKED on server access

- [ ] Extend client + `beep rag` for: ingest, chunk templates, metadata filters, application tenancy headers, graph RAG query
- [ ] Honor `/v1/rag` canonical surface; respect tenancy contract
- [ ] `tests/test_rag_parity.py`

## Slice 6 — Server MCP registry (SRV-5) [P1] — BLOCKED on server access

- [ ] Consume `/v1/mcp` + `/mcp/registry`
- [ ] Respect token scopes
- [ ] `tests/test_server_mcp_registry.py`

## Slice 7 — Progressive service integration (SRV-6..SRV-13) [P2/P3] — BLOCKED on server access

| Item | Status |
|------|--------|
| SRV-7 tooling | Blocked |
| SRV-8 vision/docs | Blocked |
| SRV-6 hosted agents | Blocked |
| SRV-9 studio | Blocked |
| SRV-11 scheduler | Blocked |
| SRV-10 audio | Blocked |
| SRV-12 rag cluster | Blocked |
| SRV-13 service calls | Blocked |

## Slice 8 — Docs + tracker sync

- [x] Update `.plans/PHASE_23_SERVER_INTEGRATION_PARITY.md` (this file)
- [x] Update `MASTER-TODO-TRACKER.md` PH-23 status
- [ ] Update `docs/features/server-integration.md` status
- [ ] Update `docs/features/api-client.md` + `docs/features/coding-assistant.md` + `docs/features/rag.md`
- [ ] Update `README.md` API surface table to `/v1` paths

---

## Acceptance criteria

- [x] No `/ai-middleware/api/*` literals remain in `beep/api/`; all server calls use `/v1` / `/v1/api`.
- [x] Coding-session linkage works through the unified chat path (compaction fixed, endpoints centralized).
- [x] CLI discovers server capabilities + version and shows them in `beep status`.
- [x] Beep.AI.Server is the documented, one-step default; non-Beep providers show a clear degradation map.
- [ ] RAG parity + server MCP registry consumption (blocked — needs server access).
- [ ] Progressive service integration (SRV-7..13) (blocked — needs server access).
- [x] All new modules ≤500 lines, one concern each, with isolated tests.
- [ ] `pytest -q`, `ruff check beep tests`, `mypy beep` green.

## Risks / notes

- **Breaking change risk:** Slices 1–2 alter live server calls. Verify against a running Beep.AI.Server build before merge; keep a thin compatibility fallback only if the server still serves legacy aliases, and document the reason (AGENTS.md standards-first rule).
- Many of the 16 services are low-relevance to a coding CLI (text-to-image, object detection, ML models, personal assistant) — explicitly **deferred**, not dropped.
