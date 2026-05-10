# Phase 7 — Session History & Compaction

**Goal:** Session history must be reliably written, resumable, and
self-healing when a context window overflows. Agent runs need the same
persistence that chat sessions have.

**Current status (2026-05-05):** `SessionSummary`, parsed timestamp handling,
schema migration, flushed appends, shared session-file scanning,
`export_session(...)`, `search_sessions(...)`, atomic `replace_session(...)`,
agent-run JSONL persistence with terminal `meta` sentinels, `/resume` +
`/sessions list` session UX, and automatic local history compaction are now
implemented in the `sessions` domain.

---

## Todo Tracker

### Fixes

- [x] **Agent graph execution persists runs to session history.**
  `run_graph_impl(...)` appends the agent goal up front, step execution appends
  assistant/tool turns, and terminal execution appends a `{"role": "meta", "reason": "..."}`
  sentinel for both run and resume flows.

- [x] **history.py — `list_sessions` returns `SessionSummary` objects with parsed timestamps.**
  The `/sessions` slash command shows sessions as raw JSONL filenames. Timestamps
  should be parsed from the filename (which encodes the ISO datetime) and shown as
  human-readable relative times ("3 hours ago").
  Fix: add `SessionSummary` dataclass with `session_id`, `created_at`, `message_count`,
  `last_message_preview`.

- [x] **commands/session.py — `/resume` is registered and restores session state.**
  `ResumeCommand` is present in the command registry, advertises its description,
  and restores `_session_id`, `_messages`, counters, linkage IDs, and output state
  through `repl_context_support.resume_session(...)`.

- [x] **history.py — JSONL writes flush immediately and session replacement uses the shared atomic writer.**
  If the process is killed mid-run the last message may be partially written.
  Fix: use atomic write (write to `.tmp` then rename) for the final flush, or at minimum
  flush after each `append_message` call.

### Enhancements

- [x] **history.py — `export_session(session_id, format: "md" | "json")` is implemented.**
  Exports a session as readable Markdown (with role headings) or raw JSON array.
  Used by the `/sessions export` slash command.

- [x] **history.py — Automatic compaction when session exceeds token budget.**
  After every 10 appended messages, `ChatSession._save(...)` now checks
  `estimate_tokens(all_messages)` through `maybe_compact_session(...)` and rewrites
  persisted history with `replace_session(...)` when the threshold is crossed.
  The local compacted window is now wired; explicit server-side compaction remains
  available through `/compact` when the endpoint exists.

- [x] **commands/session.py — `/sessions list` table with relative timestamps exists.**
  `SessionsCommand._list()` renders `build_sessions_table(...)` with session ID,
  relative created time, message count, and last-message preview.

- [x] **sessions/ — `search_sessions(query)` is implemented.**
  Full-text search across all JSONL history files for sessions containing `query`.
  Returns a list of `SessionSummary` with the matching message snippets.
  Used by a future `/sessions search <query>` command.

- [x] **sessions domain — consolidate duplicate JSONL scanning and atomic-write behavior.**
  Session-file scanning previously lived in parallel loops inside `history.py`.
  Fix: keep scanning, schema migration, and atomic write helpers in
  `sessions/history_support.py`, leaving `history.py` as the public facade.

---

## Acceptance Criteria

1. Agent runs write to JSONL history with a `meta/reason` sentinel at end.
2. `list_sessions()` returns `list[SessionSummary]` with parsed timestamps.
3. `/resume <session-id>` restores chat session correctly.
4. Auto-compaction triggers when token estimate crosses the threshold.
5. `/sessions export` produces valid Markdown or JSON output.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/sessions/history.py` | ✅ Public session-history facade |
| `beep/sessions/history_support.py` | ✅ Schema migration, scanning, and atomic write support |
| `beep/agent/graph_execution.py` | ✅ Agent run/resume history persistence + terminal sentinels |
| `beep/chat/repl.py` | ✅ Automatic local compaction wired into chat persistence |
| `beep/chat/commands/session.py` | ✅ /resume implementation and /sessions list table |
| `beep/commands/sessions.py` | ✅ export command |
| `tests/test_phase7_sessions.py` | ✅ Session history, compaction, and agent persistence assertions |
