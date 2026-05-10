# Beep.AI.Code — Engineering Plan Index

## Purpose

This folder tracks all planned and in-progress engineering work for Beep.AI.Code.
Each phase has its own document with a todo tracker, design rationale, and acceptance criteria.
Treat this index, the individual phase files, and `../MASTER-TODO-TRACKER.md` as the canonical backlog of record when implementing ongoing roadmap work.

## Architecture Summary (as of 2026-05-05)

```
beep/
├── cli.py                      Entry point — builds Typer app, default dispatch, and core CLI callbacks
├── cli_command_registration.py Typer command/group registration + canonical registration metadata, app-derived known command tokens, and shared lazy command forwarding
├── cli_support.py              Shared CLI status/config/agent dispatch helpers
├── config.py                   BeepConfig (Pydantic), load/save, env-var overrides
├── setup_wizard.py             First-run interactive wizard
├── system_support.py           Shared status/config/diagnostics rendering + state helpers for chat and CLI
│
├── api/
│   ├── client.py               BeepAPIClient — httpx async, all server endpoints
│   ├── payloads.py             Payload builders (chat, anthropic, responses)
│   └── streaming.py            SSE parser for streaming chat completions
│
├── agent/
│   ├── loop.py                 Public agent entrypoint — selects backend and runs graph
│   ├── approval.py             Human approval gate (file_write, file_edit, shell)
│   ├── environment.py          AgentEnvironmentManager — managed venv at ~/.beepai/agents_env/
│   ├── environment_catalog.py  Pinned package catalog for the managed env (trimmed required set)
│   ├── bundle_contract.py      Portable agent bundle manifest + compatibility/runtime/provenance validation
│   ├── bundle_store.py         Portable agent bundle build/load/install helpers
│   ├── backends.py             Provider-neutral agent backend contract + implementations
│   ├── message_adapter.py      Provider payload normalization + LangChain message conversion helpers
│   ├── tool_adapter.py         BaseTool → LangChain/LangGraph tool adaptation helpers
│   ├── graph.py                LangGraph StateGraph + SQLite checkpointing for the canonical agent runtime
│   └── tools/
│       ├── base.py             BaseTool, ToolResult, optional_params
│       ├── factory.py          build_agent_tools() — local + plugin + MCP
│       ├── file_read.py        file_read — paginated, total_lines header
│       ├── file_write.py       file_write — create/overwrite
│       ├── file_edit.py        file_edit (SEARCH/REPLACE blocks) + single_edit
│       ├── search.py           search — regex, context_lines, case_sensitive
│       ├── shell.py            shell — exit_code, stderr, 10k char cap
│       └── list_directory.py   list_directory — flat or recursive
│
├── chat/
│   ├── repl.py                 ChatSession — interactive REPL
│   ├── runner.py               run_chat() entry shim
│   ├── prompts.py              System prompts (assistant, review, explain)
│   ├── stream_renderer.py      Streaming Rich renderer
│   ├── command_registry.py     Slash command registry builder
│   ├── session_runtime_state.py Session-owned task/watcher/edit runtime helpers
│   └── commands/               ~18 slash command modules
│
├── coding/
│   ├── metadata.py             build_coding_metadata() envelope
│   ├── prompt_context.py       build_workspace_system_prompt()
│   └── response_metadata.py    Parse server coding response headers
│
├── context/
│   ├── builder.py              Inject file contents into prompts
│   ├── window.py               Token budget tracking + truncation
│   └── smart.py                Smart context selection
│
├── memory/
│   └── loader.py               ProjectMemory (.beep.md / .beep/ files)
│
├── planner/
│   └── editor.py               EditPlan — multi-file atomic edits + rollback
│
├── sessions/
│   ├── history.py              Public session-history facade for JSONL storage in ~/.beepai/history/
│   ├── history_support.py      Schema migration, atomic writes, and session-file scanning helpers
│   ├── export.py               File export wrappers over canonical session export content
│   └── presentation.py         Shared session summary table rendering for chat and CLI surfaces
│
├── templates/
│   ├── generator.py            Public template facade
│   ├── catalog.py              Built-in template definitions
│   ├── discovery.py            Template pack discovery + frontmatter loading
│   ├── rendering.py            Variable prompting, generation, and display helpers
│   └── service.py              Shared template list/generate orchestration for chat and CLI surfaces
│
├── workspace/
│   ├── detector.py             find_workspace_root() — .git walk
│   ├── ignore.py               IgnoreMatcher — .beepignore/.gitignore via pathspec
│   ├── editing.py              Shared edit preparation for CLI and chat mutation flows
│   ├── file_ops.py             read_file / write_file / create_diff
│   ├── view.py                 Shared file-read and tree-display validation for CLI and chat surfaces
│   ├── search.py               Shared regex workspace scanning for CLI, chat, and agent surfaces
│   ├── search_replace.py       SEARCH/REPLACE block parser + fuzzy matcher
│   ├── file_tree.py            Rich tree display
│   └── git.py                  git status / diff / log / blame helpers
│
├── runtime/
│   └── workspace.py            WorkspaceRuntime — lru_cache per workspace
│
├── plugins/                    Plugin discovery + registry
├── rules/                      .beep/rules/ loader + resolver
├── skills/                     Skill definition loader + resolver
└── mcp/                        MCP bridge (optional, disabled by default)
```

## Coding Agent Direction

- The LangGraph migration is scoped to the **autonomous coding agent** surfaces only.
- Canonical autonomous-agent entrypoints are `beep agent ...` and the `/agent` slash command inside chat.
- Standard `beep chat` and `beep ask` remain on the existing chat/session runtime and should not pick up a LangGraph dependency as a side effect of Phase 11.
- Product priority is **Beep.AI.Server first**. The provider-neutral backend seam exists so the same coding-agent core can later target compatible OpenAI-style backends such as **LM Studio** and **Ollama** without rewriting the graph.
- Semble-backed semantic code search should become a **first-class coding-agent capability** for exploratory retrieval, separate from both provider backends and LSP editor operations.
- Model providers and workspace-intelligence capabilities should evolve as **plugins with typed capability flags** rather than growing hardcoded branches in the agent core.
- The follow-on provider roadmap should extend the existing `AgentBackendProvider` and `BackendProviderPlugin` seams with first-class provider packs rather than replacing the current provider architecture.
- Portable agent deployment should use one canonical bundle contract that local runners, Beep.AI.Server registration, npm packages, wheel-based runners, GitHub release assets, and container wrappers can all consume.
- Local runtime domains such as sessions and templates should keep public entry modules thin and move duplicated file I/O, discovery, parsing, rendering, and formatting into domain-owned support modules instead of mixed god-files.

## Data-Flow at Runtime

```
CLI entry (cli.py / beep)
        │
        ├── chat → ChatSession (repl.py)
        │           ├── slash commands (command_registry → commands/)
        │           ├── @file mentions (context/builder.py)
        │           └── LLM turn (chat_completion_stream → api/client.py)
        │
        ├── agent → run_agent() (loop.py)
        │           ├── backend selection (backends.py)
        │           ├── provider/message normalization (message_adapter.py)
        │           ├── LangGraph state machine (graph.py)
        │           └── tool adaptation/execution seam (tool_adapter.py)
        │
        └── ask / review / test / lint → dedicated commands (commands/)
                    └── all call api/client.py methods
```

Phase 11 changes the `agent` branch in that flow. It does not migrate the standard `chat` or `ask` branches to LangGraph.

## Phase Index

| Phase | File | Focus | Status |
|-------|------|-------|--------|
| 1 | [PHASE_1_TOOLS.md](PHASE_1_TOOLS.md) | Agent tool layer fixes & new tools | Complete |
| 2 | [PHASE_2_AGENT_LOOP.md](PHASE_2_AGENT_LOOP.md) | Agent loop reliability & quality | Complete (superseded by LangGraph runtime in Phase 11) |
| 3 | [PHASE_3_API_CLIENT.md](PHASE_3_API_CLIENT.md) | API client completeness & resilience | Complete |
| 4 | [PHASE_4_CONTEXT.md](PHASE_4_CONTEXT.md) | Context management & prompt quality | Complete |
| 5 | [PHASE_5_CHAT_REPL.md](PHASE_5_CHAT_REPL.md) | Chat REPL UX & slash commands | Complete |
| 6 | [PHASE_6_MEMORY_RULES.md](PHASE_6_MEMORY_RULES.md) | Memory, rules, and skills | Complete |
| 7 | [PHASE_7_SESSIONS.md](PHASE_7_SESSIONS.md) | Session history & compaction | Complete |
| 8 | [PHASE_8_WORKSPACE.md](PHASE_8_WORKSPACE.md) | Workspace utilities | Complete |
| 9 | [PHASE_9_PLUGINS_MCP.md](PHASE_9_PLUGINS_MCP.md) | Plugin system & MCP bridge, including safe post-init verification of real MCP tool contracts for launch-only presets from captured JSON or live stdio discovery | Complete |
| 10 | [PHASE_10_TESTS.md](PHASE_10_TESTS.md) | Test coverage gaps | Complete (96 test files, 1083 tests) |
| 11 | [PHASE_11_LANGGRAPH.md](PHASE_11_LANGGRAPH.md) | Provider-neutral LangGraph runtime + managed agent venv | Complete |
| 12 | [PHASE_12_PROVIDER_AND_LSP_PLUGINS.md](PHASE_12_PROVIDER_AND_LSP_PLUGINS.md) | Provider plugins + Semble/LSP workspace intelligence | Complete |
| 13 | [PHASE_13_PRODUCT_PARITY.md](PHASE_13_PRODUCT_PARITY.md) | Trust, sandbox, REPL orchestration, MCP, TUI, and release parity | Complete |
| 14 | [PHASE_14_PACKAGING_AND_UPDATES.md](PHASE_14_PACKAGING_AND_UPDATES.md) | Packaging, distribution, install, upgrade, and migration lifecycle | Complete |
| 15 | [PHASE_15_CODING_AGENT_PARITY.md](PHASE_15_CODING_AGENT_PARITY.md) | TodoWrite, parallel execution, sub-agents, streaming, auto-verification | Complete |
| 16 | [PHASE_16_PROVIDER_PACKS_AND_CAPABILITY_PARITY.md](PHASE_16_PROVIDER_PACKS_AND_CAPABILITY_PARITY.md) | First-class provider packs and capability parity follow-on to the existing provider plugin seam, including real streamed completions, selected provider options, structured-output forwarding on OpenAI-style transports, multimodal vision contract support, public CLI flags for structured output and file or image-backed initial multimodal input, and an explicit provider-parameter audit boundary | Complete |
| 17 | [PHASE_17_PORTABLE_AGENT_BUNDLES_AND_RUNNER_TARGETS.md](PHASE_17_PORTABLE_AGENT_BUNDLES_AND_RUNNER_TARGETS.md) | Portable agent bundle contract, export/import flows, local runner-target execution, Beep.AI.Server interop, JavaScript SDK parity, and validation/provenance hardening are complete | Complete |
| 18 | [PHASE_18_PUBLISHING_CHANNELS_AND_DEPLOYMENT_TARGETS.md](PHASE_18_PUBLISHING_CHANNELS_AND_DEPLOYMENT_TARGETS.md) | Complete: package and deployment adapters now share one provenance and release metadata contract, all supported local channels emit release metadata artifacts, Beep.AI.Server hosted deployment works through the portable bundle import endpoint, and CI/docs explicitly cover the no-credentials dry-run validation path | Complete |
