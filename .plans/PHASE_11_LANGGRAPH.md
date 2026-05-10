# Phase 11 — Provider-Neutral LangGraph Agent Runtime

**Goal:** Replace the hand-rolled agent loop with a **LangGraph StateGraph** that is **provider-neutral** at its core and runs from a **managed Python environment**.

**Product target:** This runtime is for the **autonomous coding agent** experience only: a Claude Code / Codex-style agent that can inspect a workspace, call tools, edit files, resume work, and operate primarily against **Beep.AI.Server**.

It is **not** a plan to rewrite every Beep.AI.Code interaction around LangGraph. The intended rollout order is:

1. **Beep.AI.Server first** as the primary and best-supported coding-agent backend.
2. **Generic OpenAI-compatible backends second** through the same internal contract.
3. Concrete OpenAI-compatible targets such as **LM Studio** and **Ollama** later, once their tool-calling behavior is validated against the agent contract.

This phase is no longer defined as “LangGraph on top of Beep.AI.Server coding assistant.” That coupling is too narrow. The autonomous coding agent must be able to run against:

- `Beep.AI.Server` with optional `coding_assistant` metadata
- Generic OpenAI-compatible `/v1/chat/completions` backends
- Future backends behind the same internal contract without rewriting the graph

The managed runtime pattern remains the same: LangGraph is installed on demand into `~/.beepai/agents_env/` via `beep agent setup`, so the main CLI install stays light.

---

## Architectural Correction

The previous version of this phase planned to adapt `BeepAPIClient` directly into the graph. That is the wrong seam.

**Correct seam:**

- The graph owns **messages, tool definitions, approvals, checkpoints, and stop conditions**.
- A backend adapter owns **how a model call is made**.
- Beep-specific `coding_assistant` metadata is an **optional backend feature**, not part of the graph contract.

This means the agent runtime must treat “tool-calling chat model” as an internal abstraction, not “Beep coding assistant session.”

There is also **no legacy-compatibility requirement** for the old hand-rolled `AgentSession` execution path. Once the graph path is complete and validated, `run_agent()` should use it as the canonical implementation.

There is also **no requirement** that normal `chat`, `ask`, or inline assistant turns move to LangGraph in this phase. Those surfaces remain on their current chat/session architecture unless a later phase changes them intentionally.

The current hardcoded backend classes are acceptable as a **bootstrap seam** for Phase 11, but they are not the desired long-term integration shape for every provider. Provider plugins and LSP capability plugins are the next architectural layer after the LangGraph runtime is stable.

---

## Reviewed Scope Boundary

The current codebase already supports the intended isolation boundary:

- `beep agent ...` goes through `beep/commands/agent.py` → `beep/agent/loop.py` → `beep/agent/graph.py`
- `/agent` inside chat delegates into the same `run_agent()` entrypoint
- normal `beep chat` goes through `beep/chat/runner.py` + `beep/chat/repl.py`
- normal `beep ask` goes through `beep/commands/ask.py`

That means changing the autonomous coding agent runtime to LangGraph **does not need to change the rest of the coding product**. The graph runtime is a dedicated execution engine for the autonomous agent surface, not a replacement for all chat flows.

This boundary must remain explicit in the plan and in implementation review.

---

## Why LangGraph Still Fits

LangGraph still solves the right runtime problems:

| Capability | Hand-Rolled Loop | LangGraph |
|---|---|---|
| Durable resume | Manual / absent | `SqliteSaver` checkpoints every node transition |
| Tool execution routing | Custom loop | `ToolNode` + `tools_condition` |
| Human approval pauses | Ad hoc | Explicit interrupt / approval node boundary |
| State visibility | Private mutable fields | Explicit graph state |
| Multi-provider model usage | Needs custom abstraction anyway | Works once the backend seam is clean |

LangGraph is the orchestration runtime. It should **not** dictate a single model provider.

---

## Managed Runtime Decision

LangGraph stays out of `pyproject.toml` required dependencies.

**Why:**

- `beep chat` / `beep ask` users should not pay the LangGraph dependency cost
- PyInstaller bundle size should not absorb LangGraph
- We want freedom to evolve the agent runtime separately from the base CLI install

**Managed runtime shape:**

- Virtualenv: `~/.beepai/agents_env/`
- Status/config: `~/.beepai/agents_env_config.json`
- Required packages should be trimmed to only what the graph path truly needs:
  - `langgraph>=0.4`
  - `langchain-core>=0.3`
  - `langgraph-checkpoint-sqlite>=2.0`
  - `pydantic>=2.0`
- Optional packages:
  - `langsmith`

`langchain` top-level should **not** be required unless a concrete implementation proves it is needed.

---

## Todo Tracker

### A. Managed Agent Environment

- [x] **Keep `beep/agent/environment.py` and `beep/agent/environment_catalog.py` as the dedicated runtime manager.**
  Refine them so the catalog reflects the minimized required set above and stays provider-neutral.

- [x] **Keep `beep agent setup/status/reinstall/uninstall` as the operator surface.**
  These commands are already the correct operational boundary and should remain the way LangGraph is installed and maintained.

- [x] **Preserve the hard gate in `run_agent()`.**
  If the managed env is not ready, fail fast with `Run "beep agent setup" first.`

### B. Provider-Neutral Backend Contract

- [x] **Create `beep/agent/backends.py`.**
  This becomes the core abstraction layer for model providers.

  Required contract:
  - `AgentModelBackend` protocol / abstract base
  - `complete(messages, tools, *, stream=False) -> AgentCompletion`
  - `AgentCompletion` carries:
    - assistant text
    - normalized tool calls
    - usage
    - raw provider payload when needed for debugging

- [x] **Implement `BeepAgentBackend`.**
  Uses `BeepAPIClient` and may pass `coding_assistant` metadata **only** when configured and applicable.

- [x] **Implement `OpenAICompatibleAgentBackend`.**
  Uses direct HTTP against a generic `/v1/chat/completions` surface and ignores Beep-only metadata.

- [x] **Normalize tool-call output across providers.**
  The graph must consume one internal tool-call shape regardless of backend.

- [x] **Add agent-specific config fields to `BeepConfig`.**
  Minimum:
  - `agent_backend`: `"beep" | "openai-compatible"`
  - `agent_base_url`
  - `agent_api_key`
  - `agent_model`

  Fallback rules:
  - If agent-specific values are absent, `beep` backend may fall back to `server_url`, `api_token`, and `default_model`
  - `openai-compatible` backend may also fall back to shared values when the user intentionally points both surfaces at one endpoint

- [x] **Expose these values through CLI config UX.**
  `config` and `config-set` must show and edit the new agent backend settings.

### C. LangGraph Runtime

- [x] **Create `beep/agent/tool_adapter.py`.**
  Adapt existing `BaseTool` implementations into LangGraph-compatible tools.

  Requirements:
  - derive `args_schema` from the existing JSON Schema-like `parameters`
  - preserve approval checks
  - raise structured tool errors for failed tool execution
  - preserve output truncation limits

- [x] **Create `beep/agent/message_adapter.py`.**
  This is the message seam between provider payloads and LangGraph/LangChain message objects.

  Responsibilities:
  - OpenAI-style dict message → LangGraph-compatible message object
  - LangGraph message object → OpenAI-style dict message
  - normalized backend tool calls → `AIMessage.tool_calls`
  - tool results → `ToolMessage`

  This is preferred over a Beep-specific `BaseChatModel` adapter because the graph should not be locked to one client type.

- [x] **Create `beep/agent/graph.py`.**
  Build the actual StateGraph.

  Required state shape:
  - `messages`
  - `steps_executed`
  - `tool_calls_executed`
  - `files_touched`
  - `run_reason`
  - `final_message`

  Required nodes:
  - `agent` — calls the selected backend through `AgentModelBackend`
  - `tools` — executes adapted tools through a real LangGraph `ToolNode` wrapped by graph-local guard logic
  - `approval` — explicit approval boundary for destructive operations before `ToolNode` execution

  Required behaviors:
  - `SqliteSaver` checkpoints under `.beep/agent_state.sqlite`
  - explicit max-step and total-tool-call guards
  - explicit repeated-call guard
  - final `AgentRunResult` returned from graph state

- [x] **Replace `run_agent()` with the graph path.**
  Do not keep the current hand-rolled loop as the canonical runtime.

  `run_agent()` should:
  - assert managed env readiness
  - inject `site-packages`
  - build runtime/tools/system prompt
  - select backend from config
  - call `run_graph(...)`

- [x] **Remove the hand-rolled `AgentSession` loop.**
  Remaining tests now target `run_graph`, `AgentGraphRunner`, or `run_agent()` behavior instead of a second runtime implementation.

- [x] **Add `beep agent resume <thread_id>`.**
  Resume from SQLite checkpoint.

### D. Surface Integration

- [x] **Update standalone CLI `beep agent ...` to use backend selection.**
  This is the main provider-neutral coding-agent surface.

- [x] **Update `/agent` inside chat to use the same backend selection where practical.**
  If the chat session config selects `openai-compatible`, `/agent` should not silently hard-code Beep server behavior.

- [x] **Keep normal `chat` and `ask` out of scope for this phase.**
  Code review confirms `beep chat` and `beep ask` still use their existing chat/session path and do not require LangGraph or the managed agent environment.

- [x] **Keep the rollout Beep-first even though the core is provider-neutral.**
  The autonomous agent must feel like a first-class coding surface for Beep.AI.Server first; other OpenAI-compatible backends are extensions of the same seam, not equal-priority architecture drivers during Phase 11.

### E. Tests

- [x] **`tests/test_agent_environment.py` — managed env lifecycle.**

- [x] **`tests/test_agent_backends.py` — backend contract.**
  Cover:
  - Beep backend request shape
  - OpenAI-compatible backend request shape
  - tool-call normalization
  - coding metadata only attached for Beep backend

- [x] **`tests/test_agent_message_adapter.py` — message conversion.**
  Cover assistant/tool/tool-call round-trips.

- [x] **`tests/test_agent_tool_adapter.py` — tool adaptation.**

- [x] **`tests/test_agent_graph.py` — graph behavior.**
  Current coverage uses a fake LangGraph loader so graph orchestration stays testable even when the main dev env does not have LangGraph installed.

- [x] **Update `tests/test_agent_run_agent.py`.**
  These tests should assert backend selection and graph delegation, not legacy `AgentSession` construction.

### F. Documentation / Plan Index

- [x] **Update `.plans/README.md`.**
  Reflect `backends.py` and `message_adapter.py` in the architecture summary and note that the agent runtime is provider-neutral.

---

## Acceptance Criteria

1. `pip install beep-ai-code` still does **not** install LangGraph into the main CLI environment.
2. `beep agent setup` provisions the managed runtime successfully on Windows, Linux, and macOS.
3. `beep agent "fix the failing test"` runs via LangGraph when `agent_backend="beep"`.
4. `beep agent "fix the failing test"` also runs via LangGraph when `agent_backend="openai-compatible"` against a generic OpenAI-style backend.
5. The graph core does **not** require Beep-specific `coding_assistant` metadata.
6. `coding_assistant` metadata is only attached by `BeepAgentBackend`.
7. `run_agent()` delegates to the graph runtime as the canonical implementation.
8. `beep agent resume <thread_id>` resumes from the SQLite checkpoint.
9. `beep chat` and `beep ask` continue to use the existing non-LangGraph chat path.
10. The managed LangGraph environment is required for the autonomous coding agent surface, not for the standard chat/ask path.

---

## Out of Scope for Phase 11

- Non-OpenAI provider-native transports such as Anthropic-specific Messages API or Gemini-specific APIs. Those can be added later as more `AgentModelBackend` implementations.
- First-class LM Studio- or Ollama-specific adapters. For now they are treated as future consumers of the `openai-compatible` backend seam once compatibility is validated.
- Provider plugin registries and LSP/code-intelligence plugin registries with typed `exists` capability flags. That belongs to the follow-on provider/LSP phase.
- Multi-agent orchestration or supervisor graphs.
- Migrating normal `chat` and `ask` to the same provider-neutral runtime.
- Preserving the current hand-rolled agent loop as a supported compatibility path.
