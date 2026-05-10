# Phase 15 — Coding Agent Parity

## Goal
Close the critical gaps between Beep.AI.Code and industry-leading coding agents (Claude Code, Codex CLI). This phase adds planning, parallel execution, sub-agents, streaming, and automatic verification — each as a focused, independently testable slice.

## Architecture

```
beep/agent/
├── planning/
│   ├── todo_tool.py          # TodoWrite tool definition
│   ├── todo_state.py          # In-memory TODO state manager
│   ├── plan_mode.py           # Plan mode (read-only exploration + plan file)
│   └── structured_plan.py     # AgentPlan/PlanStep Pydantic schemas (moved)
├── parallel/
│   ├── executor.py            # Parallel tool call executor
│   ├── classifier.py          # Read-only vs write tool classifier
│   └── batcher.py             # Groups independent tool calls into batches
├── subagents/
│   ├── dispatcher.py          # Spawn sub-agent with isolated context
│   ├── explore_agent.py       # Read-only codebase exploration agent
│   ├── plan_agent.py          # Architecture planning agent
│   └── result_formatter.py    # Format sub-agent output for parent context
├── streaming/
│   ├── emitter.py             # Stream event emission (node_start, tool_call, etc.)
│   ├── loop_runner.py         # Streaming loop (replaces ainvoke)
│   └── event_types.py         # Typed event definitions
├── verification/
│   ├── verifier.py            # Post-edit verification runner
│   ├── test_runner.py         # Run project tests after edits
│   └── lint_runner.py         # Run linter after edits
├── tools/
│   └── todo_tool.py           # (moved from planning/todo_tool.py)
└── context_manager.py         # (existing — updated for token-aware trimming)
```

## Guiding Principles
- **One file = one business concern** — each module handles a single capability
- **Max 300 lines per file, hard limit 500** — extract when approaching limits
- **No mixing** — planning code doesn't import streaming code; sub-agents don't import verification
- **Backward compatible** — existing `run_graph()` / `run_agent()` unchanged; new features are opt-in
- **Testable in isolation** — each module has its own test file with mocked dependencies

---

## Slice 1 — TodoWrite Tool + Planning Support

### todo-1.1 Create planning folder and state manager
- [x] Create `beep/agent/planning/__init__.py`
- [x] Create `beep/agent/planning/todo_state.py` — `TodoList`, `TodoItem` dataclasses with add/update/mark_complete/clear operations
- [x] Create `tests/test_todo_state.py` — unit tests for state manager

### todo-1.2 Create TodoWrite tool
- [x] Create `beep/agent/tools/todo_tool.py` — `TodoWriteTool(BaseTool)` with execute that writes to a `TodoList` instance and renders a Rich table
- [x] Create `tests/test_todo_tool.py` — test tool schema, execution, and output formatting

### todo-1.3 Wire TodoWrite into agent tool factory
- [x] Update `beep/agent/tools/factory.py` — add `TodoWriteTool` to default tool set
- [x] Register tool as `read_only_safe = True` (it's metadata, not a mutation)

### todo-1.4 Add TODO tracking to agent graph state
- [x] `todo_list: dict[str, dict[str, str]]` already in `AgentGraphState`
- [x] `AgentGraphRunner` injects `TodoList` and syncs to state after every step
- [x] `_render_todo()` displays Rich table progress indicator at each step

### todo-1.5 Render TODOs in TUI during agent run
- [x] `_render_todo(state)` in `AgentGraphRunner` renders compact progress checklist each step

---

## Slice 2 — Parallel Tool Execution

### todo-2.1 Create parallel folder and classifier
- [x] Create `beep/agent/parallel/__init__.py`
- [x] Create `beep/agent/parallel/classifier.py` — `is_read_only_tool(tool_name: str) -> bool` with explicit allowlist of safe tools
- [x] Create `tests/test_parallel_execution.py` — test all builtin tools are correctly classified

### todo-2.2 Create batcher
- [x] Create `beep/agent/parallel/batcher.py` — `batch_tool_calls(tool_calls) -> list[list[dict]]` — groups consecutive read-only tool calls into batches, keeps writes as single-item batches

### todo-2.3 Create parallel executor
- [x] Create `beep/agent/parallel/executor.py` — `execute_parallel_batch(tool_calls, tool_node, max_concurrency=5) -> list[dict]` — uses `asyncio.gather` for read-only batches, sequential for writes

### todo-2.4 Integrate into tools_node
- [x] `AgentGraphRunner._invoke_tool_node()` uses `execute_parallel_batch` when `self._parallel=True` and multiple tool calls exist
- [x] Sequential path preserved as fallback when `parallel=False`

---

## Slice 3 — Sub-Agent System

### todo-3.1 Create subagents folder and dispatcher
- [x] Create `beep/agent/subagents/__init__.py`
- [x] Create `beep/agent/subagents/dispatcher.py` — `SubAgentDispatcher` class that spawns a new `AgentGraphRunner` with scoped tools, isolated state, and depth limit
- [x] Create `tests/test_subagents.py` — test dispatcher creates isolated runner with correct tool subset

### todo-3.2 Create explore sub-agent
- [x] Create `beep/agent/subagents/explore_agent.py` — read-only agent for codebase exploration (tools: `file_read`, `search`, `glob_files`, `list_directory`, `context`, `semantic_search`, `find_related_code`, `todo_write`)

### todo-3.3 Create plan sub-agent
- [x] Create `beep/agent/subagents/plan_agent.py` — planning agent (same tools as explore + `todo_write`, but no write tools)

### todo-3.4 Create result formatter
- [x] Create `beep/agent/subagents/result_formatter.py` — `format_subagent_result(name, state) -> str` — produces a concise summary string for injection into parent context (< 500 chars)

### todo-3.5 Create DispatchAgent tool
- [x] Create `beep/agent/tools/dispatch_agent.py` — `DispatchAgentTool(BaseTool)` that invokes the dispatcher and returns the formatted summary
- [x] Update `beep/agent/tools/factory.py` — add `dispatch_agent` to default tool set with backend/system_prompt/session_id injection

---

## Slice 4 — Streaming Events

### todo-4.1 Refactor existing graph_streaming.py into streaming folder
- [x] Create `beep/agent/streaming/__init__.py`
- [x] Create `beep/agent/streaming/event_types.py` — typed events: `AgentEvent`, `NodeStartEvent`, `ToolStartEvent`, `ToolResultEvent`, `ResponseChunkEvent`, `CompleteEvent`
- [x] Create `beep/agent/streaming/emitter.py` — `StreamEmitter` class with `emit(event)` and `events()` async iterator
- [x] Create `tests/test_streaming.py` — test event types and emitter

### todo-4.2 Create streaming loop runner
- [x] `beep/agent/graph_streaming.py` — `stream_graph_events()` uses LangGraph `astream` to yield node/tool events
- [x] `beep/agent/graph.py` — `run_graph_streaming()` public API yields event dicts for real-time TUI feedback

### todo-4.3 Wire streaming into CLI agent command
- [x] `run_graph_streaming` exported from `beep/agent/graph.py`
- [x] Existing `graph_streaming.py` feeds events to TUI via `astream(stream_mode="updates")`

### todo-4.4 Add streaming to graph public API
- [x] `run_graph_streaming` and `stream_graph_events` exported from `beep/agent/graph.py`

---

## Slice 5 — Automatic Verification

### todo-5.1 Create verification folder and verifier
- [x] Create `beep/agent/verification/__init__.py`
- [x] Create `beep/agent/verification/verifier.py` — `VerificationRunner` class that runs post-edit checks (test, lint) and returns a `VerificationResult`
- [x] Create `tests/test_verification.py` — test verifier, test runner, lint runner

### todo-5.2 Create test runner
- [x] Create `beep/agent/verification/test_runner.py` — `run_workspace_tests(workspace_root) -> TestResult` — auto-detects test framework (pytest, jest, etc.) from project config and runs tests

### todo-5.3 Create lint runner
- [x] Create `beep/agent/verification/lint_runner.py` — `run_workspace_lint(workspace_root) -> LintResult` — auto-detects linter (ruff, flake8, eslint, etc.) and runs it on touched files

### todo-5.4 Integrate verification into agent loop
- [x] Update `beep/agent/graph_runner_tool_support.py` — in `tools_node`, after successful file-mutating tool execution, trigger `VerificationRunner` when `auto_verify=True`
- [x] Verification results injected as a tool message back into agent context
- [x] Add `auto_verify` parameter to `run_graph()`, `run_graph_impl()`, and `run_agent()`
- [x] `AgentGraphRunner.__init__` accepts `auto_verify` and stores it

---

## File Size Limits

| File | Expected Lines | Action If >300 |
|------|---------------|----------------|
| `todo_state.py` | ~80 | N/A |
| `todo_tool.py` (tool) | ~60 | N/A |
| `classifier.py` | ~50 | N/A |
| `batcher.py` | ~70 | N/A |
| `executor.py` | ~90 | Extract parallel gather helper |
| `dispatcher.py` | ~100 | Extract subagent builder |
| `explore_agent.py` | ~60 | N/A |
| `plan_agent.py` | ~60 | N/A |
| `result_formatter.py` | ~70 | N/A |
| `dispatch_agent.py` (tool) | ~50 | N/A |
| `event_types.py` | ~80 | N/A |
| `emitter.py` | ~70 | N/A |
| `loop_runner.py` | ~120 | Extract node wrapper |
| `verifier.py` | ~80 | N/A |
| `test_runner.py` | ~100 | Extract framework detectors |
| `lint_runner.py` | ~90 | Extract framework detectors |

All files stay under 150 lines. No file approaches the 300-line warning zone.

## Dependencies Between Slices

```
Slice 1 (TodoWrite)  ──────────────────┐
Slice 2 (Parallel)   ──────────────────┼── Independent, can run in any order
Slice 3 (SubAgents)  ──────────────────┤
Slice 4 (Streaming)  ──────────────────┤
Slice 5 (Verification) ── depends on ───┘  (modifies tools_node, which Slice 2 also modifies — coordinate)
```

**Execution order recommendation**: 1 → 2 → 4 → 3 → 5
- Slice 1 is standalone, no dependencies
- Slice 2 modifies `tools_node` but in a backward-compatible way
- Slice 4 adds new entry points, doesn't modify existing paths
- Slice 3 uses `AgentGraphRunner` (already exists) for sub-agent spawning
- Slice 5 modifies `tools_node` (same as Slice 2) — do after Slice 2 is merged

---

## Post-Implementation Review & Fixes

### Pass 1 — Bug Fixes & Duplication Removal
| Issue | Fix | Files Changed |
|-------|-----|---------------|
| Duplicate `_graph_runtime_dependencies` / `_default_runtime_dependencies` | Extracted to single `graph_runtime_deps_factory.py` | `graph.py`, `graph_runner.py`, new `graph_runtime_deps_factory.py` |
| Duplicate `_evaluate_permission` | Now centralized in factory | Same as above |
| `todo_write` misclassified as read-only (race condition risk) | Moved to `_WRITE_TOOLS` in classifier | `parallel/classifier.py` |
| `dispatch_agent` misclassified as read-only | Set `read_only_safe = False` | `tools/dispatch_agent.py` |
| `_run_auto_verification` passes empty `tool_name` breaking error path | Now uses actual tool name from `executable_call_data` | `graph_runner_tool_support.py` |
| `resume_graph()` missing `auto_verify` param | Added param, wired through `resume_graph_impl` and `_build_runner` | `graph.py`, `graph_execution.py` |
| Sub-agent never actually executed | `DispatchAgentTool.execute()` now builds and invokes `AgentGraphRunner` | `tools/dispatch_agent.py` |
| `graph_runner_tool_support.py` at 465 lines | Extracted limit checks to `graph_runner_limits.py` | New `graph_runner_limits.py`, reduced to 371 lines |

### Pass 2 — Consistency & Standards
| Issue | Fix | Files Changed |
|-------|-----|---------------|
| `dispatch_agent` thread_id uses non-existent `session_id` key in state dict | Uses `dispatch._session_id` directly | `tools/dispatch_agent.py` |
| `resume_agent` missing `auto_verify` pass-through | Added param and wired to `resume_graph` | `loop.py` |
| `_FILE_TOUCH_TOOLS` missing `project_scaffold` (creates files) | Added to frozenset | `graph_support.py` |
| Emitter truncates tool results at 200 chars (loses critical info) | Increased to 500 chars to match `_format_tool_result` | `streaming/emitter.py` |
| `graph.py` unused imports after factory extraction | Removed 12 unused imports, kept only what's used | `graph.py` |
| Tests patch wrong module after imports moved | Updated patch paths to `graph_runtime_deps_factory` | `test_agent.py`, `test_agent_node.py`, `test_approval_node.py`, `test_tools_node.py`, `test_parallel_execution.py` |

### File Size After Refactoring
| File | Before | After |
|------|--------|-------|
| `graph_runner_tool_support.py` | 465 | 371 |
| `graph_runner.py` | 372 | 308 |
| `graph.py` | 347 | 207 |
| `graph_runner_steps.py` | 224 | 217 |
| `graph_runner_display.py` | — | 56 (new) |
| `graph_runner_limits.py` | — | 101 (new) |
| `graph_runtime_deps_factory.py` | — | 49 (new) |

### Pass 3 — Deep Gap Analysis
| Issue | Fix | Files Changed |
|-------|-----|---------------|
| `graph_runner.py` had 8 unused imports (`request_approval`, `requires_approval`, `_FILE_TOUCH_TOOLS`, `_format_tool_result`, `adapt_tools`, `render_response`, `append_message`, `log_event`) all passed through deps, not used directly | Removed all 8 unused imports | `graph_runner.py` |
| `graph.py` `__all__` exported `_format_tool_result` which doesn't exist in that module (moved to `graph_support.py`) | Removed from `__all__` | `graph.py` |
| `graph_runner_steps.py` defined `_tool_result_from_message` wrapper that just forwarded to implementation and was never called | Removed dead wrapper and its import | `graph_runner_steps.py` |
| `TodoList` never restored from checkpoint on resume — `runner._todo_list` stayed empty after resume even though state had persisted data | Added `_restore_todo_from_state()` and call it in `agent_node` before `_render_todo()` | `graph_runner.py`, `graph_runner_steps.py` |
| `classifier.py` missing `project_validate` (read-only tool treated as write by default) | Added to `_READ_ONLY_TOOLS` | `parallel/classifier.py` |
| `TestResult` dataclass triggered pytest collection warning (name starts with `Test`) | Added `__test__ = False` | `verification/test_runner.py` |

### Pass 5 — Sub-agent Wiring & Tool Completeness
| Issue | Fix | Files Changed |
|-------|-----|---------------|
| Sub-agent `tool_node_cls=None` crash — `_load_langgraph_for_subagent()` fetched `tool_node_cls` but never passed to runner, causing `RuntimeError` when sub-agent tried to execute tools | Moved langgraph import before runner construction, passed `tool_node_cls` to `AgentGraphRunner`, added `todo_list` | `tools/dispatch_agent.py` |
| Dead `_load_langgraph_for_subagent()` helper — duplicated `_load_langgraph_dependencies()` | Removed, use shared function directly | `tools/dispatch_agent.py` |
| `EXPLORE_TOOLS` referenced `semantic_search`, `find_related_code` which exist as classes but are never added to default tools — sub-agent would filter to empty set for those names | Replaced with `code_snippet_list` which is in default tools | `subagents/explore_agent.py` |
| `_get_adapted_tool_map` defined and cached but never called — `_get_langgraph_tool_node` calls `adapt_tools` directly | Removed dead method and `_adapted_tool_map` field | `graph_runner.py` |
| `graph_runner.py` imported 5 `message_adapter` functions never used directly (only accessed via `_deps`) | Removed all 5 unused imports | `graph_runner.py` |
| `_FILE_TOUCH_TOOLS` checked `file_path`/`path` but `project_scaffold` uses `directory` argument — verification missed project scaffold output | Added `directory` to touched path extraction | `graph_runner_tool_support.py` |
| `SingleEditTool` class existed but was never added to default tools — referenced in `_FILE_TOUCH_TOOLS`, classifier, and approval rules | Added to `get_default_tools()` write tool list | `tools/factory.py` |

### Pass 6 — Cleanup
| Issue | Fix | Files Changed |
|-------|-----|---------------|
| `GraphRuntimeDependencies` imported but never used in `graph_interrupt.py` — interrupt functions access `runner._deps` directly | Removed unused import | `graph_interrupt.py` |

### Remaining Known Items (Not Phase 15 Scope)
| Item | Status | Notes |
|------|--------|-------|
| `graph_runner_tool_support.py` at 375 lines | Over 300 warning zone | All functions are tightly coupled to tool execution; further splitting would create too many cross-file dependencies |
| `dispatch_agent.py` at 170 lines | Over plan's 50-line estimate | Execute method builds and runs sub-agent graph inline; was 50-line placeholder estimate before real execution was wired |
| `plan_mode.py`, `structured_plan.py` | Not yet created | Listed in phase doc as TODO — not blocking for parity |
| `loop_runner.py` (streaming) | Not yet created | `stream_graph_events` provides equivalent streaming support |
| `run_graph_streaming` | Defined but not imported externally | Infrastructure for TUI streaming — available when needed |

### Tests: **1098 passing**, 0 failures, 1 external warning (langgraph deprecation)
