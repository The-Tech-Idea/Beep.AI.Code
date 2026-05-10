# Beep.AI.Code — MASTER TODO TRACKER

Single roadmap for **enhancements** after README review. Each phase is a self-contained execution slice: **target files**, **checklists**, **implementation steps**, **verification**.

**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done

---

## Canonical Phase Tracker

Broad implementation or "continue" requests must follow this tracker together with the referenced phase docs unless the user explicitly changes priority.

| Phase | Status | Plan File | Execution Note |
| ----- | ------ | --------- | -------------- |
| PH-1 | [x] | `.plans/PHASE_1_TOOLS.md` | Tool-layer hardening complete; move to the next in-progress phase unless reprioritized. |
| PH-2 | [x] | `.plans/PHASE_2_AGENT_LOOP.md` | Superseded by Phase 11 LangGraph runtime — tool truncation, argument validation, limit logic, run_reason accuracy, streaming, retry, AgentRunResult, and auto_approve are all handled in the LangGraph agent. |
| PH-3 | [x] | `.plans/PHASE_3_API_CLIENT.md` | All items implemented: `_request()` with BeepAPIError, retry on 429/503, configurable timeout, embeddings/RAG methods, streaming with tool-call sentinels, `/status` prefers `v1_health` when token configured. |
| PH-4 | [x] | `.plans/PHASE_4_CONTEXT.md` | All items implemented: `CODE_AGENT` prompt with tool guidance, `build_tool_list_section`, pair-safe `truncate_messages`, context omit warning, `TOKENS_PER_CHAR_ESTIMATE = 0.35`, `SmartContextBuilder` with `select_context_files()`, workspace_root in coding metadata. 24 tests pass. |
| PH-4 | [x] | `.plans/PHASE_4_CONTEXT.md` | Complete: CODE_AGENT prompt with tool guidance, build_tool_list_section, pair-safe truncate_messages, context omit warning, TOKENS_PER_CHAR_ESTIMATE=0.35, SmartContextBuilder with select_context_files(), workspace_root in coding metadata. 24 tests pass. |
| PH-5 | [x] | `.plans/PHASE_5_CHAT_REPL.md` | Complete: command aliases support in base class + registry, UndoCommand, AskCommand, /compact keeps last 6 messages, /status model tiers, Ctrl-C streaming handling, tool-call rendering in stream renderer. |
| PH-6 | [x] | `.plans/PHASE_6_MEMORY_RULES.md` | Complete: ProjectMemory.to_prompt_section(), AgentMemory class, MemoryReloadCommand, skill injection in build_workspace_system_prompt, rules resolver with multi-file union. |
| PH-9 | [x] | `.plans/PHASE_9_PLUGINS_MCP.md` | Complete: plugin/MCP runtime hardening is finished, including managed MCP discovery files, verified preset launch metadata, static contracts for doc-backed vendors, and safe `beep mcp verify-tools <server>` workflows for upgrading launch-only presets with validated real tool listings from either `--from-file <json>` payloads or live `--discover` stdio tool discovery. |
| PH-10 | [x] | `.plans/PHASE_10_TESTS.md` | Complete: 96 test files, 1083 tests passing. All P1/P2/P3 coverage items addressed. |
| PH-11 | [x] | `.plans/PHASE_11_LANGGRAPH.md` | Provider-neutral LangGraph runtime and managed autonomous-agent environment are complete. |
| PH-12 | [x] | `.plans/PHASE_12_PROVIDER_AND_LSP_PLUGINS.md` | Provider/plugin and workspace-intelligence capability work is complete. |
| PH-13 | [x] | `.plans/PHASE_13_PRODUCT_PARITY.md` | All workstreams complete: trust/sandbox enforcement, auto workspace context, REPL orchestration state, MCP runtime hardening, TUI workbench, and release hardening. |
| PH-14 | [x] | `.plans/PHASE_14_PACKAGING_AND_UPDATES.md` | All workstreams complete: install channels, distribution strategy, upgrade UX, managed runtime compatibility, migration/repair policy, and CI/release gates. This phase remains scoped to the main CLI package and managed runtime lifecycle, not portable agent publishing. |
| PH-15 | [x] | `.plans/PHASE_15_CODING_AGENT_PARITY.md` | All five slices complete: TodoWrite + planning, parallel tool execution, sub-agent dispatch with backend injection, streaming events, and auto-verification wired into the agent loop. Six post-implementation review passes completed. Pass 1: shared runtime deps factory, misclassification fixes (todo_write/dispatch_agent), empty tool_name bug, missing auto_verify on resume, sub-agent execution wired, graph_runner_tool_support split. Pass 2: thread_id bug, resume_agent auto_verify, _FILE_TOUCH_TOOLS gap, emitter truncation, unused imports cleaned, test patch paths updated. Pass 3: graph_runner 8 unused imports removed, graph.py __all__ fixed, dead _tool_result_from_message wrapper removed, TodoList checkpoint restore on resume, project_validate added to read-only classifier, pytest collection warning fixed. Pass 4: _run_with_streaming_or_interrupt (103 lines) dead code removed, run_graph_streaming got missing todo_list/auto_verify params, graph_runner.py split into display module (308 lines from 348). Pass 5: sub-agent tool_node_cls=None crash fixed, dead _load_langgraph_for_subagent removed, EXPLORE_TOOLS fixed (replaced nonexistent tools with code_snippet_list), dead _get_adapted_tool_map removed, 5 more unused message_adapter imports removed, directory arg added to file_touched tracking, SingleEditTool added to default tools. Pass 6: unused GraphRuntimeDependencies import removed from graph_interrupt.py. 1098 tests passing. |
| PH-16 | [x] | `.plans/PHASE_16_PROVIDER_PACKS_AND_CAPABILITY_PARITY.md` | Complete: the OpenAI, Anthropic, and OpenRouter provider packs are in place; plugin-first vendor onboarding has a reusable OpenAI-compatible provider helper, README guidance for Zen-style providers, and focused registry coverage; capability follow-on work includes real streamed completion handling, selected user-facing provider options, structured-output forwarding on OpenAI-style/Beep paths, multimodal vision contract support including Anthropic image normalization, public `run_agent`/`resume_agent` exposure for structured-output plus initial multimodal inputs, public `beep agent` CLI flags for structured output and file or image-backed initial multimodal input, and an explicit audit confirming that no other provider-specific config-backed parameters remain to forward in this phase. |
| PH-17 | [x] | `.plans/PHASE_17_PORTABLE_AGENT_BUNDLES_AND_RUNNER_TARGETS.md` | Complete: Beep.AI.Code now has a canonical portable bundle manifest contract in `beep/agent/bundle_contract.py`, local export/import flows backed by `beep/agent/bundle_store.py` and `beep/commands/agent_bundle.py`, a local runner-target flow via `beep agent run <bundle_file_or_id> <goal>`, a completed Beep.AI.Server interop lane with server-side bundle mapping plus token-auth import/export endpoints, a JavaScript SDK bundle-lifecycle lane with typed import/export helpers and npm-facing package metadata hardening, and the final validation/provenance hardening slice with explicit payload validation, deterministic fixture coverage, compatibility mismatch tests, and optional provenance signature placeholders. |
| PH-18 | [x] | `.plans/PHASE_18_PUBLISHING_CHANNELS_AND_DEPLOYMENT_TARGETS.md` | Complete: local dry-run packaging, npm/Python/GitHub release/container wrappers, hosted Beep.AI.Server deployment, shared `release-metadata.json` provenance across packaging outputs, README channel guidance, and explicit no-credentials CI validation for package/deploy dry runs are all in place. |
| PH-19 | [x] | `.plans/semble.txt` | Complete: Semble semantic code-search integration. `SembleIndexAdapter` and `SemanticSearchTool` / `FindRelatedCodeTool` in `beep/agent/tools/semantic_search.py`; support helpers in `semantic_search_support.py`; per-workspace singleton in `AppService.semble_index()`; `SembleWorkspaceIntelligencePlugin` in `builtin_workspace_intelligence.py`; auto-context integration in `AutoContextBuilder`; `semble` package in `environment_catalog.py`; `semble[mcp]` MCP server preset in `beep/mcp/presets.py` with verified `SEMBLE_TOOLS` contracts in `preset_tools.py`; `semble>=0.1.1` optional dependency in `pyproject.toml[semble]` included in the `all` extra; 50+ tests across `test_semantic_search_support.py` and `test_semantic_search_tools.py`. |

---

## Phase 0 — Baseline accuracy & developer ergonomics

**Goal:** Docs and CLI UX match shipped behavior; no new product features.


| ID   | Task                                                                                                                                    | Verification                |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| P0-1 | [x] Audit all user-facing strings (`README`, Typer help, `/help`) for deprecated flags (`--agent` → `beep agent`, `--tui` → `beep tui`) | Grep + manual `beep --help` |
| P0-2 | [x] Document `project_id` in README + `beep config-set` hint                                                                            | Config round-trip           |
| P0-3 | [x] Add `beep plugins doctor` (or extend `diagnostics`) — list plugin paths, load errors, version                                       | Unit test stdout            |
| P0-4 | [x] CI snippet in README: GitHub Actions matrix for `pytest` + `ruff` on 3.11/3.12                                                      | Workflow green              |
| P0-5 | [x] README GitHub landing page: TOC, install paths (standalone vs monorepo), features summary, doc map, troubleshooting, API table      | Preview on GitHub           |


**Primary files:** `README.md`, `beep/cli.py`, `beep/commands/diagnostics.py`

---

## Phase 1 — Wire the plugin registry into runtime

**Goal:** `PluginRegistry` is not “library-only”; plugins change REPL + agent behavior.
**Status:** Implemented (runtime wiring in REPL + agent, plugin diagnostics, command integration).


| ID   | Task                                                                                                                                            | Verification                             |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| P1-1 | Define **plugin discovery order**: (a) `~/.beepai/plugins/*.py`, (b) `<workspace>/.beep/plugins/*.py`, (c) optional `BEEP_PLUGINS_DIR`          | Env + cwd tests                          |
| P1-2 | On `ChatSession` init: load directory, merge **context** into system prompt (after project memory)                                              | Integration test: context string present |
| P1-3 | Register **plugin slash commands** in REPL: merge `get_command_descriptions()` into `/help`; dispatch unknown `/foo` to `handle_plugin_command` | Async test                               |
| P1-4 | `beep agent`: append `registry.get_tools()` to `get_default_tools()`                                                                            | Agent smoke: dummy tool invoked          |
| P1-5 | `/plugins`: list loaded plugins, paths, errors                                                                                                  | Manual + unit test                       |
| P1-6 | [x] Sandboxing: document that plugin code runs **in-process** (trusted model); optional `--no-plugins`                                          | README security section                  |


**Primary files:** `beep/plugins/registry.py`, `beep/chat/repl.py`, `beep/agent/loop.py`, `beep/chat/commands/misc.py` (or new `plugins.py`), `tests/test_plugins_integration.py` (new)

---

## Phase 2 — Skills layer (Cursor / Codex-style)

**Goal:** Declarative **skill** documents (markdown + frontmatter) the CLI can auto-inject when the user’s intent matches, without shipping Python per skill.


| ID   | Task                                                                                                                                                         | Verification                |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------- |
| P2-1 | **Skill schema** (YAML frontmatter): `name`, `description`, `triggers` (keywords/globs), `inject`, `priority`                                                | Schema tests                |
| P2-2 | Search paths: `~/.beepai/skills/**/*.md`, `<workspace>/.beep/skills/**/*.md`                                                                                 | Fixture workspace           |
| P2-3 | **Resolver**: on each user message (or `/skill <name>`), rank skills; inject top-N within a **token budget** (chars or rough estimate)                       | Test over-budget truncation |
| P2-4 | `/skills`, `/skill off`: list active, disable session overrides                                                                                              | REPL tests                  |
| P2-5 | Optional sync: `GET` from server **if** Beep exposes a stable token-auth “skills pack” endpoint later; start with **local-only** to avoid blocking on server | N/A for v1                  |


**Primary files:** `beep/skills/` (new package: `loader.py`, `resolver.py`, `models.py`), `beep/chat/repl.py`, `beep/chat/commands/misc.py`

---

## Phase 3 — Rules engine (repo + user)

**Goal:** Combine **AGENTS.md / CLAUDE.md-style** rules with machine-checkable overrides (glob → rule text).


| ID   | Task                                                                                                                                                                                         | Verification            |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| P3-1 | Load order: server default (none) → `~/.beepai/rules.md` → `<workspace>/AGENTS.md` → `<workspace>/.beep/rules.md` → `.beep.md` (already loaded as memory; avoid duplicate unless configured) | Golden-file test        |
| P3-2 | `.beep/rules/` optional: `00-base.md`, `10-python.md` with glob frontmatter `applies_to: "**/*.py"`                                                                                          | Resolver merges by path |
| P3-3 | `/rules`: show which files contributed which blocks (debuggability)                                                                                                                          | Snapshot test           |
| P3-4 | Align naming with Beep.AI.Server **AGENTS.md** vocabulary where overlap exists                                                                                                               | Doc cross-link only     |


**Primary files:** `beep/rules/` (new), `beep/memory/loader.py` (coordination), `beep/chat/repl.py`

---

## Phase 4 — Templates v2 (server-aware + user packs)

**Goal:** Go beyond built-in string templates in `beep/templates/generator.py` and keep template behavior in domain-owned modules instead of one mixed generator file.


| ID   | Task                                                                                                   | Verification                      |
| ---- | ------------------------------------------------------------------------------------------------------ | --------------------------------- |
| P4-1 | **User template dir**: `~/.beepai/templates/*.md` with same variable syntax as today                   | `beep template list` shows source |
| P4-2 | **Workspace templates**: `.beep/templates/<name>.md`                                                   | List + generate                   |
| P4-3 | Optional: fetch **named template** from server if API exists; cache under `~/.beepai/cache/templates/` | Feature-flagged client method     |
| P4-4 | **Template variables** from `prompt_toolkit` or `rich` Prompt for missing keys                         | Interactive test                  |
| P4-5 | [x] Split template catalog, discovery, variable resolution, and display into domain-owned modules so `generator.py` stays a thin compatibility facade | `tests/test_templates.py` + template command guards |
| P4-6 | [x] Route CLI and chat template list/generate flows through a shared templates-domain service so workspace-aware behavior and parsing stay consistent | Template/chat command regression tests |


**Primary files:** `beep/templates/generator.py`, `beep/templates/catalog.py`, `beep/templates/discovery.py`, `beep/templates/rendering.py`, `beep/templates/service.py`, `beep/commands/template.py`, `beep/chat/commands/system.py`

---

## Phase 5 — MCP bridge (optional process)

**Goal:** Attach **MCP tools** to the agent loop the way IDEs do, without forking Beep.AI.Server.


| ID   | Task                                                                                                                               | Verification                   |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| P5-1 | Config: `mcp_servers` list in `code.json` (command + args + env) — **off by default**                                              | Schema validation              |
| P5-2 | [x] Spawn MCP client subprocess / use `httpx` for streamable HTTP MCP per spec                                                     | One integration test with mock |
| P5-3 | [x] Map MCP tools into OpenAI **tool** schema for `chat_completion`                                                                | Contract test                  |
| P5-4 | [x] Security: require explicit env gate `BEEP_MCP=1` (or truthy variants)                                                          | Doc + test                     |
| P5-5 | [x] Add structured MCP execution observability (`mcp.tool.start/success/error/output_truncated`) with timeout/error coverage tests | MCP regression tests           |


**Primary files:** `beep/mcp/client.py` (extend), `beep/config.py`, `beep/agent/loop.py`

---

## Phase 6 — Coding assistant parity & observability

**Goal:** Close gaps between CLI and server capabilities visible in `ChatSession`.


| ID    | Task                                                                                                                                        | Verification                             |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| P6-1  | [x] Implement or remove stubs: `_update_coding_ids`, `_handle_coding_approvals` in `repl.py`                                                | E2E against dev server (optional marker) |
| P6-2  | [x] Structured logging mode: `BEEP_LOG_JSON=1` for tool/server events                                                                       | Log line test                            |
| P6-3  | [x] Token usage: prefer server-reported usage when present in stream/non-stream payloads; fallback to heuristic                             | Unit test with mocked payload            |
| P6-4  | [x] `/compact`: call server compaction API if available; else local summarization                                                           | Behavior doc                             |
| P6-5  | [x] Enforce `/max_tokens` budget across AI slash commands (`/retry`, `/summary`, `/clipboard`, `/image`, `/review`, `/commit`, `/pr`)       | Command regression tests                 |
| P6-6  | [x] Normalize agent termination observability (`agent.run.done` includes `reason`; emit `agent.run.empty_response`; verify summary reasons) | Agent loop regression tests              |
| P6-7  | [x] Merge default agent coding metadata (`workspace_root`, `interaction_mode`) with caller-provided overrides to preserve linkage context   | Agent metadata regression tests          |
| P6-8  | [x] Persist normal chat `send()` responses into `_last_output` for `/output` and `/clipboard --copy` parity                                 | Focused send-path regression tests       |
| P6-9  | [x] Add empty-output guardrail in main `send()` path to prevent blank assistant turns and stale-success logs                                | Focused send-path regression tests       |
| P6-10 | [x] Forward active coding metadata from chat `/agent` command into `run_agent` to keep project/session linkage intact                       | Agent command regression tests           |
| P6-11 | [x] Enforce token budget guard on chat `/agent` command to match AI command budget behavior parity                                          | Agent command regression tests           |
| P6-12 | [x] Add empty-output guardrails for one-shot CLI `ask` and `review` commands to prevent silent blank output paths                           | One-shot command regression tests        |
| P6-13 | [x] Add empty-output guardrail in TUI chat stream path and prevent blank assistant message persistence                                      | TUI regression tests                     |
| P6-14 | [x] Add graceful `KeyboardInterrupt` handling for one-shot CLI `ask` and `review` commands to avoid abrupt abort traces                     | One-shot command regression tests        |
| P6-15 | [x] Add graceful exception handling in one-shot CLI `ask` and `review` commands to avoid raw stacktrace leakage on API failures             | One-shot command regression tests        |
| P6-16 | [x] Add graceful runtime/startup exception handling in `watch` command loop with deterministic stop behavior on failure/interrupt           | Watch command regression tests           |
| P6-17 | [x] Add graceful exception handling for `workspace tree` and `workspace cat` rendering paths to avoid raw CLI crashes on file/FS errors     | Workspace command regression tests       |
| P6-18 | [x] Add graceful runtime exception handling for top-level `chat` and `agent` CLI commands to avoid abrupt crash traces                      | Command runtime-error regression tests   |
| P6-19 | [x] Add graceful runtime/interrupt handling parity for `lint`, `test`, and `rag` command entrypoints to avoid abrupt `asyncio.run` failures | Command runtime-error regression tests   |
| P6-20 | [x] Add graceful runtime/interrupt handling for `tui` command entrypoint to avoid abrupt launcher failures                                  | TUI command regression tests             |
| P6-21 | [x] Add graceful exception guards for `analyze` and `template` command core execution paths to avoid abrupt command crashes                 | Analyze/template guardrail tests         |
| P6-22 | [x] Add graceful exception guards for `edit` and `sessions` command paths to avoid filesystem/history crash leakage                         | Sessions/edit guardrail tests            |
| P6-23 | [x] Isolate watcher callback failures in `WatchRuleHandler` so one bad callback does not break file-event processing                        | Watcher service regression tests         |
| P6-24 | [x] Add top-level failure guard in `diagnostics` command to prevent abrupt crashes during config/plugin discovery failures                  | Diagnostics command regression tests     |
| P6-25 | [x] Ensure `status` always closes API client on failures and validate `config-set` numeric parsing errors with friendly CLI output          | CLI guardrail regression tests           |
| P6-26 | [x] Enforce strict `sessions export --format` validation (`markdown`/`json`) to prevent silent fallback behavior                            | Sessions command regression tests        |
| P6-27 | [x] Add `config-set` persistence failure guard so save/write errors return friendly CLI failures instead of raw exceptions                  | CLI guardrail regression tests           |
| P6-28 | [x] Add timeout guard for `execute_watch_event` to prevent hung commands from stalling watch workflows                                      | Watcher service regression tests         |
| P6-29 | [x] Improve watcher failure messaging to include command exit code when stderr/stdout are empty                                             | Watcher service regression tests         |
| P6-30 | [x] Add `config-set` numeric range validation (`max_tokens > 0`, `temperature` in `[0,2]`) to prevent invalid runtime configuration         | CLI config validation tests              |
| P6-31 | [x] Harden watcher timeout cleanup so timeout result remains deterministic even when process kill/drain fails                               | Watcher service regression tests         |
| P6-32 | [x] Add explicit watch callback runtime error reporting in `watch_cmd` so callback loop failures are user-visible                           | Watch command regression tests           |
| P6-33 | [x] Add graceful `setup` command interrupt/runtime failure handling to prevent abrupt setup wizard crashes                                  | CLI guardrail regression tests           |
| P6-34 | [x] Fix default CLI one-shot prompt parsing to preserve multi-word questions while respecting `-m/--model` flag parsing                     | CLI default dispatch tests               |
| P6-35 | [x] Fix default one-shot dispatch when flags precede prompt (`beep --model ... <question>`) so prompt detection remains correct             | CLI default dispatch tests               |
| P6-36 | [x] Forward `--mode` in default one-shot dispatch path so `beep <question> --mode ...` honors intended ask mode                             | CLI default dispatch tests               |
| P6-37 | [x] Fix default CLI subcommand detection to only evaluate the leading token, preventing prompt-word collisions (`setup`, `test`, etc.)      | CLI default dispatch tests               |
| P6-38 | [x] Converge chat slash-command and CLI status/config/diagnostics presentation through shared helpers so equivalent system surfaces stop drifting | Chat system-command + diagnostics regression tests |
| P6-39 | [x] Centralize canonical CLI command tokens in `cli_command_registration.py` so default dispatch and registered command groups do not drift      | CLI default-dispatch + smoke regression tests |
| P6-40 | [x] Make CLI top-level and grouped Typer registration metadata the single source of truth so command names stop drifting inside `cli_command_registration.py` | CLI registration + smoke regression tests |
| P6-41 | [x] Derive known CLI command tokens from the built Typer app so unnamed core commands and explicit aliases stop depending on a separate core-command list | CLI registration + default-dispatch regression tests |
| P6-42 | [x] Register core CLI commands through the same shared registration module as auxiliary commands so Typer wiring stops being split between `cli.py` and `cli_command_registration.py` | CLI registration + smoke + agent regression tests |
| P6-43 | [x] Centralize lazy import-and-forward command dispatch in `cli_command_registration.py` so wrapper bodies stop duplicating module import plumbing | CLI wrapper + registration regression tests |
| P6-44 | [x] Centralize regex workspace scanning in `beep/workspace/search.py` so CLI grep, chat `/grep`, and the agent `SearchTool` stop carrying separate file-scan implementations | Agent search + workspace command + chat regression tests |
| P6-45 | [x] Centralize workspace file-view and tree-view behavior in `beep/workspace/view.py` so CLI `cat`/`tree` and chat `/cat`/`/tree` stop carrying separate validation and rendering paths | Workspace view + workspace command + chat regression tests |
| P6-46 | [x] Centralize workspace edit preparation in `beep/workspace/editing.py` so standalone `edit` and chat edit flows stop duplicating prior-content loading and undo-payload construction | Workspace editing + edit command + chat runtime regression tests |
| P6-47 | [x] Persist chat task and watcher runtime state on `ChatSession` through shared session-runtime helpers so `/task` and `/watch` survive multiple commands in one session and reset cleanly on `/clear` | Chat session command + clear/reset regression tests |


**Primary files:** `beep/chat/repl.py`, `beep/api/client.py`, `beep/chat/stream_renderer.py`

---

## Phase 7 — Session history & compaction


| ID   | Task                                                                 | Verification     |
| ---- | -------------------------------------------------------------------- | ---------------- |
| P7-1 | [x] Persist agent runs to JSONL history with goal + terminal `meta` sentinel | `tests/test_phase7_sessions.py` |
| P7-2 | [x] Register `/resume` and restore session state through shared REPL context helpers | Chat/session regression tests |
| P7-3 | [x] Render `/sessions list` with relative timestamps and previews | Session presentation + command tests |
| P7-4 | [x] Wire automatic local compaction into chat history persistence | `tests/test_phase7_sessions.py` |

Packaging and PyPI publishing lifecycle work moved to Phase 14. Use `.plans/PHASE_14_PACKAGING_AND_UPDATES.md` plus the canonical phase tracker above for that backlog.


**Primary files:** `README.md`, `pyproject.toml`, `completions/beep.bash`

---

## Dependency map (recommended order)

```text
Phase 0 → Phase 1 → Phase 2 ─┬→ Phase 4
              └→ Phase 3 ───┘
              └→ Phase 5 (parallel after P1)
Phase 6 can overlap P1+ after P0
Phase 7 last
```

---

## Quick reference — extension points today


| Mechanism                          | Status           | Notes                                 |
| ---------------------------------- | ---------------- | ------------------------------------- |
| `PluginRegistry`                   | Wired            | Phase 1 complete                      |
| Hooks (`hooks.json`)               | Wired (events)   | Extend events list in code as needed  |
| Project memory (`.beep.md`)        | Wired            | Works with rules layering             |
| Skills (`.beep/skills`)            | Wired            | Phase 2 complete                      |
| Rules (`AGENTS.md`, `.beep/rules`) | Wired            | Phase 3 complete                      |
| Templates (builtin + packs)        | Wired            | Phase 4 complete                      |
| MCP package dir                    | Wired + hardened | Subprocess execution + timeout/limits |


---

## Release Checklist

Use this checklist before publishing to PyPI:

- `python -m pip install --upgrade build twine`
- `python -m build`
- `python -m twine check dist/*`
- `pytest -q`
- `ruff check beep tests`
- `mypy beep`
- Fresh-venv wheel install smoke test
- `pipx install dist/*.whl` smoke test
- `beep --help` and `beep diagnostics` sanity checks
- Completion setup sanity check (`beep --install-completion` and `completions/beep.bash`)

---

*Last updated: Phase 7 session history and compaction work is complete, including agent-run JSONL persistence, `/resume`, `/sessions list`, and wired automatic local compaction through `ChatSession._save(...)`; template generation is split into domain-owned catalog/discovery/rendering modules behind a thin public facade; session history scanning and atomic-write behavior are centralized in `sessions/history_support.py`; shared helpers now converge chat and CLI status/config/diagnostics presentation; canonical CLI registration metadata now lives in `cli_command_registration.py`, known command tokens are derived from the built Typer app, core and auxiliary commands register through the same module, lazy import-and-forward wrapper plumbing is centralized, regex workspace scanning now lives in `workspace/search.py` so CLI/chat/agent callers share one file-scan implementation, workspace file/tree viewing now lives in `workspace/view.py` so CLI/chat callers share one validation and rendering path, workspace edit preparation now lives in `workspace/editing.py` so standalone `edit` and chat edit flows share one prior-content loading and undo-preparation path, and chat task/watcher runtime state now lives on `ChatSession` through `chat/session_runtime_state.py` so `/task` and `/watch` survive multiple commands and reset on `/clear`; token budget guard, MCP execution observability, agent termination reason logging, coding metadata defaults, send/output parity, empty-output guardrails, and chat/agent/one-shot/TUI/watch/workspace/lint/test/rag/analyze/template/edit/sessions/diagnostics/status/config/setup/default-dispatch linkage + interrupt/error/callback-failure/format-validation/timeout/failure-message/config-range/timeout-cleanup/callback-runtime/flag-order/mode-forward/subcommand-detection parity are enforced across runtime paths.*