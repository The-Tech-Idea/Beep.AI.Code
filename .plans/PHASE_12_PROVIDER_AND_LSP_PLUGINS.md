# Phase 12 — Provider Plugins And Workspace Intelligence Capability Layer

**Goal:** Move model-provider integration and workspace intelligence integration onto a **plugin-based capability system** so the coding agent can target Beep.AI.Server first, then LM Studio, Ollama, and other providers without hardcoding growing branches into the core runtime, while also making **Semble-backed semantic code search** and LSP capabilities first-class parts of the coding-agent product.

This phase is the architectural follow-on to Phase 11.

- **Phase 11** establishes the LangGraph runtime, checkpoints, approval boundaries, and provider-neutral backend seam.
- **Phase 12** turns concrete provider selection, semantic code search, and LSP/code-intelligence selection into **pluggable integrations with explicit capability descriptors**.

## Current Implementation Status

The following Phase 12 increments are now implemented in `Beep.AI.Code`:

- typed capability contracts for workspace intelligence and agent providers
- a built-in autonomous-agent provider registry for the Beep and OpenAI-compatible backends
- concrete built-in provider plugins for LM Studio and Ollama on top of the OpenAI-compatible transport seam
- runtime plugin discovery support for backend-provider plugins through the existing plugin runtime
- provider-aware agent status and provider-aware setup/runtime validation
- CLI provider discovery and configuration guidance via `beep agent providers` plus selected-provider guidance in `beep agent status`
- interactive provider configuration via `beep agent configure [provider_key]` and provider-aware fallback setup in `ensure_agent_configured()`
- provider-level connectivity probing before saving interactive agent-provider configuration, using built-in `/v1/models` validation for OpenAI-compatible providers
- formal optional guidance/probe hooks on `BackendProviderPlugin`, so runtime plugin providers can participate in discovery and validation without undocumented duck-typing
- a first-class `WorkspaceIntelligencePlugin` family in the plugin registry, with runtime capability aggregation and tool composition support
- the built-in Semble path now runs through an actual `WorkspaceIntelligencePlugin`, and `WorkspaceRuntime` sources the shared semantic-search adapter from the registry instead of constructing it directly
- workspace-intelligence status/report plumbing now also goes through the plugin registry, so `agent status` can consume plugin-provided runtime reports instead of depending on the semantic-search adapter directly
- a built-in Python/Jedi workspace-intelligence plugin that contributes real hover, definition, and reference tools plus typed LSP capability flags through the shared registry seam
- the built-in Python/Jedi workspace-intelligence plugin now also contributes real workspace-symbol search and rename support through the same adapter and plugin seam
- the managed autonomous-agent environment now installs Jedi as a required package so Python code intelligence lives in the same dedicated runtime as LangGraph and Semble
- first-party Semble and Python/Jedi workspace-intelligence tools now declare explicit `read_only_safe` behavior, with destructive Python rename routed through the approval boundary

The planned Phase 12 scope is now implemented. Future provider-specific edit flows,
broader multi-language code-intelligence plugins, and richer diagnostics/code-actions/
formatting support move to later roadmap phases rather than remaining open in this phase.

---

## Why This Must Be Separate From The LangGraph Core

LangGraph solves orchestration.
It does **not** solve:

- how different providers are discovered and configured
- which provider features exist or do not exist
- whether semantic code search is available and which retrieval operations exist
- whether a workspace has LSP support and which LSP operations are available

Those are **integration capabilities**, not graph-state concerns.

If we keep adding them directly inside `beep/agent/backends.py`, `beep/agent/loop.py`, or `beep/agent/tools/factory.py`, the coding agent will drift back into a branch-heavy coordinator instead of a clean runtime.

---

## Architectural Direction

The coding agent should compose from **three independent layers**:

1. **Runtime layer**
   LangGraph orchestration, checkpoints, approvals, tool routing, stop conditions.

2. **Provider layer**
   Model backend plugins such as Beep.AI.Server, generic OpenAI-compatible, LM Studio, Ollama, and future providers.

3. **Workspace intelligence layer**
   Semble-backed semantic code search plus LSP and related semantic-code-intelligence plugins that expose retrieval, diagnostics, definitions, references, rename, symbols, code actions, and formatting when available.

Workspace intelligence is therefore **not** a model backend concern.
Semble-style retrieval and LSP operations are separate capability/plugin families that the coding agent may use alongside any model provider.

---

## Capability Contract

The user requirement here is correct: provider and LSP integrations need a standard interface where features can say whether they **exist**.

Use a typed capability descriptor instead of ad hoc booleans spread across the codebase.

### Core Pattern

```python
@dataclass(frozen=True)
class CapabilityFlag:
    exists: bool
    notes: str = ""
```

This gets embedded into typed capability sets rather than scattering optional methods everywhere.

### Provider Capabilities

Example shape:

```python
@dataclass(frozen=True)
class ProviderCapabilities:
    chat_completion: CapabilityFlag
    tool_calling: CapabilityFlag
    streaming: CapabilityFlag
    structured_output: CapabilityFlag
    vision: CapabilityFlag
    embeddings: CapabilityFlag
    local_model_runtime: CapabilityFlag
```

### Semantic Search Capabilities

Example shape:

```python
@dataclass(frozen=True)
class SemanticSearchCapabilities:
   semantic_search: CapabilityFlag
   find_related: CapabilityFlag
   local_indexing: CapabilityFlag
   remote_git_indexing: CapabilityFlag
   hybrid_mode: CapabilityFlag
   semantic_mode: CapabilityFlag
   bm25_mode: CapabilityFlag
   language_filters: CapabilityFlag
   path_filters: CapabilityFlag
   index_stats: CapabilityFlag
```

### LSP Capabilities

Example shape:

```python
@dataclass(frozen=True)
class LSPCapabilities:
    diagnostics: CapabilityFlag
    hover: CapabilityFlag
    definition: CapabilityFlag
    references: CapabilityFlag
    rename: CapabilityFlag
    workspace_symbols: CapabilityFlag
    code_actions: CapabilityFlag
    formatting: CapabilityFlag
```

### Workspace Intelligence Capabilities

Example shape:

```python
@dataclass(frozen=True)
class WorkspaceIntelligenceCapabilities:
   semantic_search: SemanticSearchCapabilities
   lsp: LSPCapabilities
```

The coding agent must check these capabilities when deciding which tools to expose and which workflows are valid.

---

## Plugin Types To Add

The current plugin system already supports tool, command, and context plugins.
Phase 12 should add **two new plugin families**.

### A. Backend Provider Plugin

Suggested responsibility:

- identify the provider key and metadata
- expose provider capabilities
- validate provider-specific configuration
- build the runtime `AgentModelBackend`

Suggested contract:

```python
class BackendProviderPlugin(Plugin):
    @abstractmethod
    def provider_key(self) -> str: ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...

    @abstractmethod
    def build_backend(self, *, config: BeepConfig, workspace_root: Path | None,
                      coding_assistant: dict[str, Any] | None) -> AgentModelBackend: ...
```

### B. Workspace Intelligence Plugin

Suggested responsibility:

- expose which semantic search and semantic-code-intelligence operations exist
- provide Semble-backed search tools and/or direct services backed by an LSP server
- remain optional per workspace and per language

Suggested contract:

```python
class WorkspaceIntelligencePlugin(Plugin):
    @abstractmethod
   def capabilities(self, *, workspace_root: Path) -> WorkspaceIntelligenceCapabilities: ...

    @abstractmethod
    def get_tools_for_workspace(self, workspace_root: Path) -> list[BaseTool]: ...
```

This preserves the current tool-based agent architecture while letting Semble-backed retrieval and LSP-backed tools appear only when supported.

---

## Built-In Provider Strategy

Phase 12 should not start from third-party providers.
It should first convert the existing built-ins into the new plugin model.

### Required built-ins

1. **Beep backend plugin**
   Canonical, first-class provider for the coding agent.

2. **Generic OpenAI-compatible backend plugin**
   The transport-level compatibility seam.

### Follow-on provider plugins

3. **LM Studio plugin**
   Implemented as a built-in provider plugin that wraps the OpenAI-compatible transport and uses LM Studio-specific local-runtime defaults.

4. **Ollama plugin**
   Implemented as a built-in provider plugin that wraps the OpenAI-compatible transport and uses Ollama-specific local-runtime defaults.

The key rule is: **LM Studio and Ollama should not be special-cased in the graph runtime**.
They should appear as provider plugins with capability descriptors.

---

## Semble Direction

Semble should be the **first required semantic code search integration** for the coding agent.

The current regex-based `search` tool is still useful for literal confirmation and narrow exact-match checks, but it is not strong enough to be the primary exploratory retrieval path for a Claude Code / Codex-style coding agent.

Phase 12 should make Semble the default semantic retrieval path for coding-agent code discovery.

### What Semble Should Own

- intent-based code search for natural-language or symbol-like queries
- chunk-level retrieval so the agent reads less irrelevant code
- related-code discovery from a known file and line
- search modes that can distinguish hybrid, semantic-only, and lexical/BM25-only retrieval
- optional filters for languages and paths when the agent needs to narrow a large workspace
- index stats and health visibility so the runtime can expose whether the semantic-search capability is actually available
- a first-class workspace intelligence capability separate from provider backends and separate from LSP

### What Semble Should Not Replace

- exact regex/literal confirmation, which should remain available through the existing `search` tool
- LSP features such as references, rename, diagnostics, hover, and code actions
- LangGraph runtime orchestration

### Integration Direction

- Prefer an in-process Python integration or a direct wrapper around the Semble library for the coding agent runtime.
- Treat MCP mode as a compatibility path, not the primary internal integration path.
- Expose at least two Semble-backed tool surfaces for the coding agent:
  - `semantic_search`
  - `find_related_code`
- Make Semble part of the managed coding-agent environment when this phase is implemented so the autonomous coding agent has the capability by default.
- If Semble is unavailable in a context where the capability is expected, expose that through `exists = false` or a clear configuration/runtime error rather than silently pretending the feature exists.

### Primary Integration Path

- The autonomous coding agent should use the Semble Python library directly through an internal adapter built around `SembleIndex`.
- The first production implementation should target the **current local workspace** using `SembleIndex.from_path(workspace_root)`.
- Remote git indexing should remain part of the capability model because the library supports it, but it is secondary to local-workspace coding-agent use.
- The workspace runtime should cache the Semble index for the current session so agent steps do not rebuild the index on every search.
- The initial cache policy can be session-scoped and rebuilt on demand; more advanced watcher-driven refresh can follow later.

### Tool Contract To Implement

The first Semble-backed tool surfaces should map closely to the documented Semble API rather than inventing a completely different interface.

1. `semantic_search`
   Parameters should include:
   - `query`
   - `top_k`
   - `mode` with `hybrid` as default and support for `semantic` and `bm25`
   - optional `filter_languages`
   - optional `filter_paths`

2. `find_related_code`
   Parameters should include:
   - `file_path`
   - `line`
   - `top_k`

The tool adapter should accept the agent-friendly `file_path` and `line` contract even if the underlying library resolves a chunk/result object internally.

### MCP And CLI Compatibility Path

- Semble's MCP server is useful for external agent ecosystems and compatibility testing.
- Semble's CLI is useful for scripts and sub-agents.
- Neither MCP nor CLI should be the primary internal runtime path for the autonomous coding agent when the managed environment can import the Python package directly.
- The documentation notes that Claude Code and Codex CLI sub-agents cannot rely on lazy-loaded MCP schemas for Semble tools; this is another reason the internal coding-agent runtime should not depend on `mcp__semble__search` semantics.
- If a CLI fallback is ever added, it must be an explicit fallback path with clear error reporting, not a hidden silent branch.

### Retrieval Workflow Expectations

- Use `hybrid` as the default mode for general coding-agent retrieval.
- Use `semantic` for intent-heavy natural-language requests when lexical hits are weak.
- Use `bm25` for exact identifier lookups when the agent wants precise symbol matching.
- Follow the documented Semble workflow: retrieve chunks first, read full files only when the chunk is insufficient, and keep regex search for exhaustive exact-string confirmation.

---

## LSP Direction

For a Claude Code / Codex-style coding agent, LSP is important.
But the agent should never assume it exists.

The right architecture is:

- if a Semble-backed semantic-search capability is present, use it for exploratory code retrieval before falling back to regex search
- if an LSP plugin is present and healthy, expose semantic tools
- if not, fall back to file, grep, context, git, and shell tools
- never make LSP mandatory for the baseline coding agent

Semble and LSP complement each other:

- Semble handles intent-based retrieval and related-code discovery
- LSP handles precise semantic editor operations

### First useful LSP-backed tools

- `lsp_diagnostics`
- `lsp_definition`
- `lsp_references`
- `lsp_rename_preview`
- `lsp_workspace_symbols`
- `lsp_hover`
- `lsp_code_actions`

Major write operations such as rename or code actions should still flow through the approval boundary if they mutate files.

---

## Config Direction

Phase 11 keeps `agent_backend = "beep" | "openai-compatible"` as a simple bootstrap seam.

Phase 12 should evolve this toward plugin-based selection, for example:

- `agent_provider = "beep" | "openai-compatible" | "lm-studio" | "ollama" | ...`
- optional provider-specific config sections or plugin-owned validation
- workspace-intelligence/plugin config that can select `semble` as the coding agent's semantic-search provider

Do not keep expanding one flat config model forever with provider-specific fields.
Shared config stays in `BeepConfig`; provider-specific validation belongs to the provider plugin.

---

## Todo Tracker

### A. Provider Plugin Registry

- [x] Add a backend-provider plugin base type alongside the existing plugin families.
- [x] Add a provider registry/lookup layer for the coding agent runtime.
- [x] Convert the built-in Beep backend into the provider-plugin contract.
- [x] Convert the built-in generic OpenAI-compatible backend into the provider-plugin contract.

### B. Capability Descriptors

- [x] Add typed provider capability models with `exists` flags.
- [x] Add typed semantic-search capability models with `exists` flags.
- [x] Add typed LSP capability models with `exists` flags.
- [x] Ensure the coding agent only exposes workflows that match the active capability set.
   The shared autonomous-agent prompt now adds capability-aware workflow guidance based on
   the actual semantic-search and Python intelligence tools registered for the workspace.

### C. Workspace Intelligence Plugin Layer

- [x] Add a workspace-intelligence / LSP plugin base type.
- [x] Implement a Semble-backed semantic search integration for the coding agent.
- [x] Add `semantic_search` and `find_related_code` tool surfaces backed by Semble.
- [x] Map Semble search modes (`hybrid`, `semantic`, `bm25`) into the coding-agent tool contract.
- [x] Support Semble language/path filters in the coding-agent tool contract when the capability exists.
- [x] Keep the existing regex `search` tool for literal confirmation and exact-match checks.
- [x] Add the first LSP-backed tool surfaces behind capability checks.
- [x] Keep LSP optional and language/workspace dependent.

### D. Runtime Integration

- [x] Update `run_agent()` runtime preparation to resolve provider plugins rather than branching directly on backend literals.
- [x] Add Semble to the managed agent environment/package catalog for autonomous coding-agent runs.
- [x] Add per-workspace Semble index caching so repeated agent steps reuse the same index during a session.
- [x] Define how the coding agent surfaces Semble index stats/availability for diagnostics and capability checks.
- [x] Keep LangGraph runtime and state independent of provider and LSP specifics.
- [x] Ensure approval boundaries still gate destructive LSP-backed actions.

### E. Tests

- [x] Add provider-plugin registry tests.
- [x] Add capability gating tests for semantic-search features.
- [x] Add Semble-backed tool contract tests using a fake or injected Semble adapter.
- [x] Add tests for Semble mode mapping (`hybrid`, `semantic`, `bm25`).
- [x] Add tests for Semble language/path filter forwarding.
- [x] Add tests for `find_related_code(file_path, line)` resolution.
- [x] Add tests that missing Semble installation or unavailable capability returns an explicit, non-silent failure path.
- [x] Add capability gating tests for provider features.
- [x] Add LSP capability gating tests so missing features do not register tools.
- [x] Add LM Studio and Ollama plugin contract tests once those plugins exist.

---

## Acceptance Criteria

1. The coding agent runtime does not branch directly on a growing list of provider names in its orchestration core.
2. Provider integrations expose typed capability descriptors with `exists` flags.
3. Semble-backed semantic search is a first-class coding-agent capability and exposes typed capability descriptors with `exists` flags.
4. LSP integrations expose typed capability descriptors with `exists` flags.
5. Beep.AI.Server remains the primary built-in provider.
6. LM Studio and Ollama can be added as plugins without changing the LangGraph core.
7. The coding agent prefers Semble-backed retrieval for exploratory code discovery, while keeping exact regex search for literal confirmation.
8. The first Semble integration uses the in-process Python library against the current workspace and does not require MCP to be available.
9. Semble search modes and filters are exposed through a stable tool contract when the capability exists.
10. Missing LSP features do not crash the agent or register invalid tools.
11. Normal `chat` and `ask` remain outside this provider/workspace-intelligence plugin refactor unless explicitly pulled in by a later phase.

---

## Out of Scope For This Phase

- Replacing the LangGraph runtime selected in Phase 11.
- Making LSP mandatory for all coding-agent runs.
- Replacing all exact-match search behavior with Semble and removing regex/literal search entirely.
- Making MCP the required runtime dependency for the internal Semble integration path.
- Moving the standard `chat` and `ask` product surfaces onto the same provider-plugin layer.
- Implementing every third-party provider immediately.