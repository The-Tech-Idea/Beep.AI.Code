# Phase 2 — Agent Loop Reliability & Quality

**Goal:** Make the `AgentSession` execution loop production-grade.
The loop is the backbone of every agentic task. It must handle partial
failures gracefully, recover from bad tool outputs, and give the LLM every
signal it needs to self-correct — without leaking confusing state.

---

## Todo Tracker

### Fixes

- [ ] **loop.py — Tool result content truncation is too aggressive.**
  `format_tool_result` truncates display at 500 chars but the FULL result
  (`result.output or result.error`) is appended into the `tool` message with no cap.
  For a 100k-char shell output this blows the context window.
  Fix: cap `tool` message content at a configurable `max_tool_output_chars` (default 8 000)
  and append a truncation notice so the LLM knows data was cut.

- [ ] **loop.py — Empty tool arguments silently discarded.**
  If `json.loads(arguments_str)` produces a non-dict (e.g. a list), `arguments = {}` is used
  silently. The LLM gets `success=False, error="Invalid arguments"` with no explanation.
  Fix: return a clearer error message stating what was received vs what was expected.

- [ ] **loop.py — `max_tool_calls_total` stop logic is inside the inner loop.**
  When the total limit is hit the function returns inside `enumerate(tool_calls)` which
  means the last tool's result message is never added to `self._messages`. The conversation
  is left in an inconsistent state (unmatched `tool_calls` with no `tool` response).
  Fix: check the total limit before executing each tool call; after hitting the limit,
  append a synthetic tool result message indicating the limit was reached, then break cleanly.

- [ ] **loop.py — `run_reason` defaults to `"completed"` but is only set to `"completed"`
  when there are no tool calls and there is content.** If the while loop exits because
  `step >= self._max_steps` the else-branch of the while never runs, so `run_reason` stays
  at whatever it was set to last. This can log `reason=completed` for a max-steps exit.
  Fix: set `run_reason = "max_steps"` at the top of the step-limit block and remove the
  misleading default.

- [ ] **loop.py — Streaming not used.**
  `chat_completion` (non-streaming) is called in the agent loop. For long responses the user
  sees nothing until the full response arrives. Add streaming support: call
  `chat_completion_stream` when `stream=True` is configured, accumulate tool-call deltas,
  then re-assemble the tool_calls list from stream chunks.
  Note: this is a larger change — phase 2 defers it to a sub-task.

- [ ] **loop.py — No retry on transient API errors.**
  A single `Exception` from the API aborts the entire run. Transient 429/503 errors should
  be retried with back-off (max 3 retries) before marking `run_reason = "api_error"`.

### Enhancements

- [ ] **loop.py — Add `on_tool_result` callback hook.**
  Allow callers (e.g. TUI, tests) to receive tool result events without monkey-patching
  `format_tool_result`. Signature: `on_tool_result: Callable[[str, ToolResult, int], None] | None`.

- [ ] **loop.py — Expose `run()` return value.**
  `run()` currently returns `None`. Change it to return a `AgentRunResult` dataclass
  with `steps_executed`, `tool_calls_executed`, `reason`, and `final_message: str | None`.
  This makes it testable and usable by the TUI.

- [ ] **loop.py — Structured tool-error injection.**
  When a tool fails, the current code appends `result.error` as the tool message content.
  The LLM sees a bare error string. Wrap it as:
  ```
  {"error": "...", "tool": "...", "hint": "check path / args"}
  ```
  so the model can reason about what went wrong.

- [ ] **loop.py — `_messages` growth is unbounded.**
  A 200-tool-call run produces ~400 messages. At that scale the context window overflows
  silently. Integrate `context/window.py` (`truncate_messages`) after every N steps to
  keep the conversation within a configurable token budget.

- [ ] **approval.py — Bulk-approve mode.**
  Add `approve_all_session: bool` flag to `AgentSession`. When set, skip the per-tool
  Confirm prompt. Currently `auto_approve` does this but it's not exposed from `run_agent()`.
  Expose it via `--yes` / `-y` CLI flag on the `agent` subcommand.

---

## Acceptance Criteria

1. Tool message content in `self._messages` is capped at `max_tool_output_chars`.
2. Hitting `max_tool_calls_total` leaves the conversation in a consistent state
   (matching `tool_call_id` → `tool` message pairs).
3. `run()` returns `AgentRunResult`; CLI still works.
4. Transient API errors are retried up to 3 times with exponential back-off.
5. `run_reason` values are accurate for all exit paths.
6. Unit tests cover: max-steps exit, total-limit exit, API retry, empty-response exit.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/agent/loop.py` | 🔧 Multiple fixes |
| `beep/agent/approval.py` | 🔧 Add approve_all_session |
| `beep/commands/agent.py` | 🔧 Expose `--yes` flag |
| `tests/test_agent_run_agent.py` | 🔧 Extend |
| `tests/test_agent_session.py` | 🔧 Extend |
