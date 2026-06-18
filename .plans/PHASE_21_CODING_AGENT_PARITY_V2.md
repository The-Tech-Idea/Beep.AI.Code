# Phase 21 — Coding-Agent Parity v2 (Claude Code / OpenCode)

## Goal

Close the remaining parity gaps with leading terminal coding agents. Phase 15 delivered planning, parallel tools, sub-agents, streaming, and verification. This phase makes those **first-class, user-driven, and persistent**: a plan/build toggle, `@mention` subagents, a persistent agent server, parallel worktree agents, generic LSP, and broader providers.

Backing feature doc: [docs/features/coding-agent-parity.md](../docs/features/coding-agent-parity.md). Companion: [.plans/PHASE_20_INTEGRATIONS_CATALOG.md](PHASE_20_INTEGRATIONS_CATALOG.md) (skills catalog = CAP-10).

## Existing substrate (verified)

- `beep/permissions/manager.py` — `SandboxMode {READ_ONLY, WORKSPACE_WRITE, FULL_TRUST}`, `PermissionDecision`.
- `beep/agent/subagents/dispatcher.py` — `SubAgentDispatcher`, `VALID_SUBAGENT_TYPES = {explore, plan, general}`, depth-limited.
- `beep/agent/tools/dispatch_agent.py` — `DispatchAgentTool` (already invokes dispatcher).
- `beep/chat/repl.py` — REPL loop + `--mode`; `beep/tui/` — Textual app.
- `beep/agent/tools/git_tool.py` — git operations for worktree work.

## Guiding principles

- One file = one concern; ≤500 lines (split near 300).
- Reuse shipped pieces (sandbox modes, dispatcher); **do not** duplicate.
- New surfaces are opt-in and backward compatible.
- Isolated tests per module.

---

## Slice 1 — Plan/Build mode toggle (CAP-1) [start here]

A one-key switch between **Plan** (read-only) and **Build** (workspace-write), with a persistent visible banner, mapped onto existing `SandboxMode`.

### cap-1.1 Mode state
- [ ] Add `mode_state.py` under `beep/chat/` (or extend `session_runtime_state.py`): `AgentMode {PLAN, BUILD}` ↔ `SandboxMode.READ_ONLY` / `WORKSPACE_WRITE`; current mode on `ChatSession`
- [ ] `tests/test_mode_state.py`

### cap-1.2 REPL toggle + banner
- [ ] `/mode`, `/plan`, `/build` slash commands; hotkey (e.g. Ctrl-T) toggle in `beep/chat/repl.py`
- [ ] Render a persistent mode banner in the prompt/header; Plan denies write tools with a friendly message
- [ ] `tests/test_repl_mode_toggle.py`

### cap-1.3 TUI Tab toggle
- [ ] Bind `Tab` (or a dedicated key) in `beep/tui/screens/chat.py` to toggle mode; visible indicator widget
- [ ] TUI mode-switch test

### cap-1.4 Enforce in agent
- [ ] When launching `/agent` or `beep agent` from a Plan-mode session, default `--sandbox read-only` unless overridden
- [ ] Test: plan-mode agent rejects write tool

**Verification:** toggling shows the banner; Plan blocks edits/shell-writes; Build restores write access.

---

## Slice 2 — `@mention` subagents (CAP-2)

Let users route a turn to a subagent inline: `@explore find the auth flow`, `@plan design the cache`, `@general ...`.

### cap-2.1 Mention parser
- [ ] Create `beep/chat/mentions.py`: detect leading `@<type>` against `VALID_SUBAGENT_TYPES`; return `(subagent_type, remainder)`
- [ ] `tests/test_mentions.py` — valid/invalid/edge (`@unknown` passes through unchanged)

### cap-2.2 Route to dispatcher
- [ ] In `beep/chat/repl.py` turn handling: when a mention is detected, build tools via factory and invoke `SubAgentDispatcher`; inject the formatted summary back into the conversation
- [ ] Respect current mode (Plan → read-only subagent tools)
- [ ] `tests/test_repl_mentions.py` — each mention dispatches correct subagent type

### cap-2.3 Help + discoverability
- [ ] Document `@explore/@plan/@general` in `/help`; add to [docs/CLI_AND_COMMANDS.md](../docs/CLI_AND_COMMANDS.md)

**Verification:** `@explore <q>` runs the explore subagent and returns a summary without polluting main context.

---

## Slice 3 — Persistent agent server (CAP-3)

A background server holding session/run state so work survives terminal/SSH exit; reconnect to an in-flight run. Builds on greenfield `beep serve` (NF-6).

### cap-3.1 Server skeleton
- [ ] Create `beep/server/` package: `app.py` (FastAPI), `run_registry.py` (in-memory + JSONL-backed run state), `lifecycle.py`
- [ ] `beep serve` command (`beep/commands/serve.py`) with bind host/port, token auth reusing config
- [ ] `tests/test_server_app.py` — health + auth

### cap-3.2 Run persistence + reconnect
- [ ] Persist agent run state to `~/.beepai/runs/<id>.jsonl`; resume/attach endpoint streams remaining events
- [ ] `tests/test_run_reconnect.py` — start → detach → reattach yields continued events (mocked backend)

### cap-3.3 Client attach
- [ ] `beep agent --serve` / `beep agent attach <run_id>` client path
- [ ] Integration test

**Verification:** kill the client mid-run; reattach and observe continued/streamed output.

---

## Slice 4 — Parallel worktree agents (CAP-4)

Run multiple agents concurrently, each isolated in its own git worktree, with a coordinator and merge step.

### cap-4.1 Worktree manager
- [ ] Create `beep/agent/parallel/worktrees.py`: create/cleanup git worktrees via `git_tool`; map run→worktree path
- [ ] `tests/test_worktrees.py` — temp repo create/list/remove

### cap-4.2 Coordinator
- [ ] Create `beep/agent/parallel/coordinator.py`: launch N agents (cap concurrency), collect `AgentRunResult`s, summarize, optional merge/PR per worktree
- [ ] Reuse `parallel/executor.py` concurrency patterns
- [ ] `tests/test_coordinator.py` — N mock agents isolated

### cap-4.3 CLI
- [ ] `beep agent fanout "<goal>" --workers N` (or `--parallel`)
- [ ] Smoke test

**Verification:** two agents edit the same file in separate worktrees without conflict; coordinator reports both results.

---

## Slice 5 — Generic LSP client (CAP-6)

Feed diagnostics/hover/symbols from any LSP server to the model, beyond Python Jedi / tree-sitter.

### cap-5.1 LSP client
- [ ] Create `beep/lsp/` package: `client.py` (stdio JSON-RPC), `registry.py` (language→server command map)
- [ ] `tests/test_lsp_client.py` — handshake + diagnostics vs a fake server

### cap-5.2 Agent tool
- [ ] Create `beep/agent/tools/lsp_diagnostics.py`: `LspDiagnosticsTool` returning diagnostics for a file
- [ ] Register in factory (read-only safe)
- [ ] Tool contract test

**Verification:** diagnostics tool returns structured errors for a sample file with a known LSP server.

---

## Slice 6 — Provider breadth + local models (CAP-8 / INT-4)

### cap-6.1 Local providers
- [ ] Add Ollama provider pack (`beep/agent/provider_builtin_ollama.py`) and a LiteLLM gateway provider
- [ ] Per-task model switch already exists via `--model`; ensure local providers resolve
- [ ] `tests/test_providers_local.py` — mocked endpoints

### cap-6.2 Provider catalog surface
- [ ] Surface available providers/models in `beep agent providers`
- [ ] Test listing includes local entries when configured

**Verification:** configure Ollama; `beep agent providers` lists it; a run targets a local model (mocked in tests).

---

## Slice 7 — Supporting parity items

| Item | Work | Test |
|------|------|------|
| CAP-5 share link | `beep sessions export --format html` + optional server-hosted link (ties NF-11) | render test |
| CAP-9 hooks parity | expand `hooks/manager.py` events: pre/post tool, pre/post run, on-error, on-edit; document | event-fire tests |
| CAP-11 undo timeline | `/undo` + checkpoint list using `editing/rollback.py` + graph checkpoints | restore test |
| CAP-12 cost guardrails | per-run budget + price hints surfaced (ties AG-4, NF-8) | budget stop test |
| CAP-7 ACP editor bridge | thin Agent Client Protocol adapter over the Slice 3 server | protocol conformance test |

---

## Acceptance criteria

- [ ] Plan/Build toggle works in REPL and TUI; Plan strictly read-only.
- [ ] `@explore/@plan/@general` route turns to subagents with clean summaries.
- [ ] Agent runs survive client disconnect and can be reattached.
- [ ] Parallel agents run in isolated worktrees without file conflicts.
- [ ] Generic LSP diagnostics available as an agent tool for at least one non-Python language.
- [ ] At least one local provider (Ollama) selectable.
- [ ] All new modules ≤500 lines, one concern each, with isolated tests.
- [ ] `pytest -q`, `ruff check beep tests`, `mypy beep` green (Windows tmp-path caveat tracked in X-1).

## Sequencing

`Slice 1 (CAP-1)` → `Slice 2 (CAP-2)` are cheap, high-visibility, and reuse shipped sandbox + dispatcher — do them first. Then `Slice 6 (providers)`, then `Slice 3/4 (server + worktrees)`, then `Slice 5 (LSP)`, then `Slice 7` polish.

## Out of scope

- Skills marketplace (CAP-10) — delivered in PH-20.
- Desktop app packaging (separate initiative).
