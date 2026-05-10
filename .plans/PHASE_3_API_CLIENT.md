# Phase 3 — API Client Completeness & Resilience

**Goal:** `BeepAPIClient` must expose every server endpoint cleanly,
handle errors with actionable messages, and be safe to use from both
the agent loop and the chat REPL simultaneously.

---

## Todo Tracker

### Fixes

- [ ] **client.py — `_request()` swallows HTTP error bodies.**
  `response.raise_for_status()` raises `httpx.HTTPStatusError` but the response body
  (which contains the server's error message) is lost. The caller sees only the status code.
  Fix: catch `HTTPStatusError` in `_request()`, read `response.text`, and raise a typed
  `BeepAPIError` that carries `status_code`, `endpoint`, and `server_message`.

- [ ] **client.py — `chat_completion` does not use `_request()`.**
  `chat_completion` calls `client.post()` directly, bypassing any future middleware
  added to `_request()` (headers, retries, error wrapping). Consolidate.

- [ ] **client.py — `list_models` and `get_model` bypass `_request()` similarly.**
  Same issue. All JSON calls should go through `_request()`.

- [ ] **client.py — `health_check` uses `/api/health` (public) but `v1_health` uses
  `/v1/health` (token-auth).** `/status` slash command calls `health_check()` which
  never shows `coding_model_tiers`. Update `/status` to prefer `v1_health()` when a
  token is configured, with graceful fallback to `health_check()`.

- [ ] **client.py — Timeout is hardcoded to `Timeout(30.0, connect=10.0)`.**
  Long operations (embedding, large completions) time out prematurely.
  Fix: read `BeepConfig.request_timeout` (new field, default 60 s) and apply it when
  building the `httpx.AsyncClient`.

- [ ] **client.py — `compact_conversation` endpoint path is version-specific.**
  The path `/ai-middleware/api/coding-assistant/sessions/compact` is baked in.
  Move it to a constant or `BeepConfig.compact_endpoint`.

- [ ] **client.py — `responses_completion` is a deprecated alias that diverges from
  `openai_responses` signature.** Ensure it passes all kwargs through correctly or
  remove it after verifying no callers depend on it.

### Enhancements

- [ ] **client.py — Add `create_embeddings(texts, model?)` method.**
  Wraps `POST /v1/embeddings`. Needed for local RAG use cases and semantic search
  commands.

- [ ] **client.py — Add `rag_query(db_id, query, top_k?)` method.**
  Wraps the RAG query endpoint for use by the `rag` CLI commands. Currently the
  `commands/rag.py` calls the endpoint inline.

- [ ] **config.py — Add `request_timeout: float` field (default 60.0).**

- [ ] **config.py — Add `retry_on_429: bool` field (default True) and
  `max_retries: int` field (default 3).**

- [ ] **client.py — Implement retry with back-off on 429 and 503.**
  Use `retry_on_429` + `max_retries` from config. Back-off: 1 s, 2 s, 4 s.
  Log each retry attempt.

- [ ] **streaming.py — Expose tool-call deltas from SSE stream.**
  `iter_chat_sse_content` only yields text content. Tool-call deltas
  (`delta.tool_calls`) are silently dropped. For streaming agent support
  (Phase 2), add `iter_chat_sse_events` that yields typed events:
  `ContentEvent`, `ToolCallDeltaEvent`, `UsageEvent`.

---

## Acceptance Criteria

1. All `_request()`-eligible methods go through `_request()`.
2. HTTP errors carry `status_code` + server error message.
3. 429 responses are retried (up to `max_retries`).
4. `request_timeout` from config is respected.
5. `create_embeddings` and `rag_query` exist and are tested.
6. `iter_chat_sse_events` exists and correctly parses tool-call deltas.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/api/client.py` | 🔧 Multiple fixes + new methods |
| `beep/api/streaming.py` | 🔧 Add event-based SSE parser |
| `beep/api/payloads.py` | ✅ Complete |
| `beep/config.py` | 🔧 Add timeout / retry fields |
| `beep/chat/commands/system.py` | 🔧 /status → prefer v1_health |
| `tests/test_api_client.py` | 🔧 Extend with error / retry tests |
| `tests/test_api_extended.py` | ✅ Complete (new endpoints done) |
