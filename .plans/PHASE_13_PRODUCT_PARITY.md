# Phase 13 — Product Parity Hardening

**Goal:** Close the highest-leverage gaps between the current Beep.AI.Code product and a daily-driver terminal coding assistant in the class of Claude Code or Codex, without collapsing the architecture back into one giant runtime and without abandoning Beep.AI.Server as the canonical backend.

This phase starts after the core LangGraph runtime and provider/workspace-intelligence plugin seams are in place.

## Why This Is A Separate Phase

Phases 11 and 12 establish the right internal architecture:

- provider-neutral agent runtime
- managed autonomous-agent environment
- plugin-based provider and workspace-intelligence capability layers
- real Semble retrieval and real Python/Jedi code intelligence

Those phases make the product *possible*.
They do not yet make the product *competitive as a default daily tool*.

The next missing work is mostly product integration and enforcement:

- real trust and sandbox policy enforcement
- automatic workspace context for normal chat, not only agent mode
- durable in-REPL task/watch/hook orchestration
- a complete MCP runtime instead of a narrow adapter seam
- a TUI that is more than a lightweight chat shell
- release-grade CI, e2e coverage, and dependency hygiene

Packaging and upgrade lifecycle work is tracked separately in `PHASE_14_PACKAGING_AND_UPDATES.md` so this phase stays focused on the live runtime product surface.

## Competitive Gap Summary

### Already Strong

- real CLI product surface with chat, ask, agent, workspace, review, lint, test, sessions, RAG, TUI, and watch commands
- provider-neutral LangGraph coding-agent runtime with checkpoints and approval boundaries
- first-class provider plugin seam for Beep, OpenAI-compatible, LM Studio, and Ollama
- first-class workspace-intelligence seam with Semble retrieval and Python/Jedi intelligence
- broad unit and component test coverage around the runtime core

### Still Missing For Daily-Driver Parity

1. **Trust and sandboxing are not enforced deeply enough.**
   The live runtime still relies too heavily on coarse tool-name approval instead of trust-zone policy and real sandbox controls.

2. **Automatic repo context for normal chat is still shallow.**
   Smart context exists, but the default `beep chat` path is still too manual compared with strong terminal coding assistants.

3. **REPL orchestration state is still fragmented.**
   `/task`, `/watch`, hooks, and session flows need durable state across commands instead of ephemeral per-command context.

4. **MCP is present but not yet a full product feature.**
   The product needs a real MCP lifecycle and REPL wiring, not only agent-side tool adaptation.

5. **The TUI is not yet a serious operator workbench.**
   It needs file navigation, task visibility, session browsing, agent-state awareness, and command workflow surfaces.

6. **Release hardening is still behind the product claims.**
   The repo needs CI, broader e2e coverage, and stricter dependency/validation hygiene.

## Workstreams

### A. Trust Policy And Real Sandbox Modes

**Objective:** Make approval, trust zones, and sandbox modes actively shape what the runtime can do.

- Route destructive tool decisions through `permissions/manager.py` and trust-zone policy, not only `agent/approval.py`.
- Define explicit sandbox modes for agent and chat runs: read-only, workspace-write, and full-trust.
- Make shell, file mutation, git mutation, and network-affecting operations consult the active sandbox/trust state.
- Preserve human approval prompts as a last-mile boundary, but do not use them as the only enforcement layer.
- Emit clear policy failures when an action is blocked instead of silently degrading behavior.

### B. Automatic Workspace Context For Standard Chat

**Objective:** Make normal `beep chat` behave more like a coding assistant and less like a generic prompt shell.

- Wire `context/smart.py` into the normal chat request-building path.
- Use workspace-intelligence capabilities to choose between Semble retrieval, semantic symbol lookup, and exact file injection.
- Add context budgeting rules so automatic context competes fairly with pinned files, `@file` references, rules, and project memory.
- Keep the context strategy observable: users should be able to see what was selected and why.
- Ensure non-code chats and tiny repos do not pay unnecessary context overhead.

### C. Durable REPL Orchestration

**Objective:** Make background work and slash-command workflows persist cleanly inside the chat product.

- Move task-manager state onto `ChatSession` instead of command-local dictionaries.
- Move watcher state onto `ChatSession` instead of command-local dictionaries.
- Turn hooks into live automation boundaries with explicit event triggers, not only configuration CRUD.
- Fix the mismatch between `sessions/history.py` return types and `commands/sessions.py` expectations.
- Make slash-command behavior and standalone command behavior converge where they represent the same operator intent.

### D. MCP Runtime Hardening

**Objective:** Make MCP a first-class, observable, durable runtime feature.

- Define how chat sessions acquire and hold MCP client/runtime state.
- Make `/mcp` commands operate on real session state instead of optional context placeholders.
- Add connection/status/error reporting for configured MCP servers.
- Decide the boundary between agent-only MCP tool adaptation and chat-visible MCP management.
- Preserve the current conservative read-only and approval defaults for external tools.

### E. TUI Workbench

**Objective:** Promote the Textual app from a lightweight shell to a real coding workbench.

- Add a real file/session/task navigation surface.
- Add visible agent run state, approvals needed, and action history.
- Add session browser and resume affordances.
- Add a command palette or equivalent workflow entry point.
- Ensure TUI behavior stays aligned with CLI commands instead of becoming a second product with different semantics.

### F. Release Hardening And Operational Readiness

**Objective:** Make the product release-grade instead of feature-rich-but-fragile.

- Add CI workflows for lint, tests, and packaging checks.
- Add end-to-end CLI scenarios that exercise setup, chat, agent, sessions, and RAG flows against controlled fakes or fixtures.
- Add higher-confidence TUI smoke coverage.
- Resolve dependency gaps on optional-but-real surfaces such as web search and plugin schema validation.
- Tighten release-readiness checks so README claims match automated validation.

## Todo Tracker

### A. Trust, Policy, Sandbox

- [x] Define the canonical trust/sandbox modes for Beep.AI.Code.
- [x] Route destructive runtime decisions through `PermissionManager` policy instead of tool-name checks alone.
- [x] Enforce sandbox mode in shell execution.
- [x] Enforce sandbox mode in file mutation and git mutation paths.
- [x] Add tests that blocked operations fail explicitly under restrictive trust modes.

Implemented: Beep.AI.Code now uses canonical `SandboxMode` values (`read-only`,
`workspace-write`, `full-trust`) across `beep agent`, `/agent`, and `/sandbox`.
The LangGraph approval seam evaluates tool calls through `PermissionManager` and now
distinguishes policy-denied operations from approval-gated ones, so blocked actions emit
explicit tool failures and `--yes` no longer bypasses sandbox policy. Read-only mode filters
mutating tools out of the agent tool set up front, while shell, file mutation, and git write
operations are enforced again at runtime through `PermissionManager` before execution.

### B. Automatic Context

- [x] Wire `context/smart.py` into the normal chat session path.
- [x] Define how Semble retrieval and explicit file context compose under a token budget.
- [x] Add capability-aware selection between Semble, Python/Jedi, and regex/file context.
- [x] Expose selected auto-context in a user-visible debug/status surface.
- [x] Add tests for default chat behavior with and without available workspace-intelligence plugins.

Implemented: Normal `beep chat` now automatically injects workspace context through
`beep/context/auto_context.py`, which composes Semble semantic retrieval (when the adapter
is available), smart file selection (git-modified, keyword-matched, recently accessed files),
and a workspace summary fallback under a configurable token budget (~24 000 chars default).
The `/context` slash command shows the current auto-context status, semantic search availability,
and supports `/context on|off` toggling. The send path (`repl_runtime_support.py`) injects
auto-context before pinned files, rules, and skills, and prints a dim status line showing which
sources were used. Capability-aware selection gracefully degrades when Semble or other plugins
are unavailable. 11 new tests cover builder behavior, Semble integration, error handling, budget
truncation, and session toggle.

### C. REPL State And Sessions

- [x] Persist task-manager state on `ChatSession`.
- [x] Persist watcher state on `ChatSession`.
- [x] Wire hook execution events into the actual REPL/runtime lifecycle.
- [x] Repair `commands/sessions.py` to match the real `SessionSummary` shape.
- [x] Converge chat slash-command and standalone CLI system status/config/diagnostics presentation through shared helpers where the operator intent overlaps.
- [x] Converge regex workspace search behavior across CLI `grep`, chat `/grep`, and the agent `SearchTool` through shared workspace-domain helpers.
- [x] Converge file-view and tree-view behavior across CLI `cat`/`tree` and chat `/cat`/`/tree` through shared workspace-domain helpers.
- [x] Converge workspace edit preparation across standalone `edit` and chat edit flows so both surfaces load prior file state and build undo payloads through shared workspace-domain helpers.
- [x] Add tests that `/task`, `/watch`, and session flows survive multiple commands in one chat session.

Implemented: `ChatSession` now lazily loads `HookConfig` via a `hook_config` property,
and `run_hooks()` is invoked at five canonical lifecycle events: `session_start` (before
welcome), `session_end` (on REPL exit), `pre_command` / `post_command` (around every
slash-command execution, with post firing even on command errors via `finally`), and
`pre_send` / `post_send` (around each LLM turn). Hook outputs render in dim style on the
console, and 20 tests cover the hook manager (load/save/toggle), `run_hooks()` execution
(stdout, stderr, timeout, error, multi-hook), and REPL wiring (command pre/post, send
pre/post, post-hook on error). Multi-turn integration tests verify that `/task` start/status/cancel
flows share a single manager across commands, `/watch` add/remove/list flows share a single watcher,
`/clear` nullifies both and subsequent commands create fresh instances, and `/undo`/`/session`
survive across turns with correct message counts.

### D. MCP Runtime

- [x] Define canonical MCP session ownership for chat and agent flows.
- [x] Inject live MCP runtime/client state into slash-command execution.
- [x] Add `/mcp` status and error-path tests against real session state.
- [x] Clarify which MCP operations are read-only versus approval-gated.
- [x] Add resilience around MCP server startup, shutdown, and transport failure handling.

Implemented: `ChatSession` now owns a cached MCP runtime snapshot for slash-command use,
`beep agent` continues to resolve MCP state per invocation, and `/mcp status|servers|tools`
now render from real session state instead of optional ad-hoc context injection. Error paths
for MCP resolution/client construction are now visible through session state and covered by tests.
MCP tool declarations now support explicit `read_only_safe` and `requires_human_approval`
metadata, the graph approval seam honors that metadata before falling back to legacy tool-name
checks, and `/mcp tools` exposes the current policy while existing external tool definitions
still default to conservative read-only and approval behavior until explicitly classified.
The MCP subprocess adapter now also terminates child processes cleanly on timeout, cancellation,
and transport-layer communicate failures, returning stable startup/timeout/transport error shapes
instead of leaving cleanup to best effort behavior.

### E. TUI

- [x] Build a real file/session/task navigation layout in the TUI.
- [x] Surface agent state, approvals, and progress in the TUI.
- [x] Add session browser and resume UI.
- [x] Add command-dispatch UX that reuses existing command logic where possible.
- [x] Add TUI smoke/integration tests beyond single-view rendering.

Implemented: The TUI has been rebuilt from scratch as an OpenCode-style terminal workbench with
a modular architecture under `beep/tui/`. The new `TUIApp` pushes a `ChatScreen` that provides a
main chat area with message rendering (markdown, code blocks, bash commands), a sidebar showing
session title, modified files, and tool calls, and a status bar with Plan/Build mode indicator,
model name, session ID, and token usage. The interface is fully keyboard-driven with bindings:
`Ctrl+P` command palette (fuzzy-searchable), `Ctrl+S` session switcher, `Ctrl+O` model selector,
`Ctrl+F` file picker (workspace-scanned with filtered directories), `Ctrl+N` new session, `Ctrl+K`
compact, `Ctrl+?` help dialog, `Tab` Plan/Build mode toggle, and `Ctrl+C` quit. Seven new focused
modules keep each file under 500 lines: `app.py`, `screens/chat.py`, `dialogs/command_palette.py`,
`dialogs/session_switcher.py`, `dialogs/model_selector.py`, `dialogs/file_picker.py`,
`dialogs/permission.py`, `dialogs/help.py`, `widgets/message_display.py`, `widgets/tool_call.py`,
`widgets/status_bar.py`, and `widgets/sidebar.py`. 20 tests cover widgets, dialogs, app behavior,
and file scanning logic.

### F. Release Hardening

- [x] Add GitHub Actions or equivalent CI workflows for the repo.
- [x] Add end-to-end CLI smoke coverage for setup, chat, agent, sessions, and RAG.
- [x] Audit optional runtime dependencies and either declare or remove them.
- [x] Make plugin schema validation deterministic instead of best-effort.
- [x] Add a release checklist tied to README feature claims.

Implemented: CI now runs the full test suite instead of only 3 focused agent tests, with a new
`e2e-smoke` job that exercises CLI smoke tests, command guards, setup wizard, diagnostics, workspace
commands, session history, hook lifecycle, and task/watch/session flow integration. Plugin schema
validation now fails closed (returns `False` with an error log) when `jsonschema` is unavailable,
instead of silently returning `True`. Three new optional dependency groups are declared in
`pyproject.toml`: `schema` (jsonschema), `websearch` (beautifulsoup4), and `all` (both). Two new
deterministic schema validation tests verify that valid schemas pass and invalid ones fail with
jsonschema installed, and that bad plugin tools are rejected with proper error messages.
22 new e2e CLI smoke tests cover all major command flows: setup (help, status), sessions
(list empty/with data, help), agent (help, status, setup help), workspace (tree, grep, cat),
diagnostics (diagnostics, doctor), templates (list, help), plugins (paths, help), MCP (help, list),
quality (lint, test help), and ask (requires config). Tests use CliRunner with targeted mocking
to exercise command wiring, argument parsing, and output rendering end-to-end without a live server.
The release readiness checklist (`tools/ci/check_release_readiness.py`) validates 76 structural
claims across all feature areas and runs as a CI gate before packaging. It verifies that every
module, CLI command, and feature area claimed in the README actually exists and is importable.

Code quality audit completed: consolidated duplicated `_build_capabilities()` across 3 provider
classes into `_default_capabilities()` helper and `LocalOpenAICompatibleProvider` base class in
`beep/agent/provider_base.py`, reducing `provider_builtin_openai.py` from 284 to 157 lines.
Extracted shared fake fixtures from `test_agent_graph.py` (597 → ~200 lines) into a focused
`test_agent_graph_nodes.py` split file. Created `beep/utils/console.py` singleton and
`beep/cli_support_async.py` async runner to replace 68 duplicated `Console()` instances and
8 duplicated `asyncio.run(_run())` patterns.

## Acceptance Criteria

1. Normal `beep chat` automatically assembles useful repo context without requiring the user to manually enumerate every relevant file.
2. Sandbox/trust modes actively constrain shell and file mutation behavior instead of acting as display-only preferences.
3. In-chat task, watch, and hook flows preserve state across commands in one session.
4. `/mcp` commands operate on a real live runtime surface, not optional placeholder context.
5. The TUI can be used as a practical daily-driver shell for chat, agent, sessions, and workspace actions.
6. The repo has release-grade CI and broader end-to-end validation for the product claims made in `README.md`.
## Out Of Scope For This Phase

- Replacing the LangGraph runtime chosen in Phase 11.
- Replacing the provider/plugin architecture from Phase 12.
- Shipping every possible language-intelligence backend immediately.
- Turning Beep.AI.Code into a fully standalone model host.
- Rewriting Beep.AI.Server to match this plan; server-side changes should stay isolated to real contract requirements.