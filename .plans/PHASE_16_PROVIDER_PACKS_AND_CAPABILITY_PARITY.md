# Phase 16 — Provider Packs And Capability Parity

**Goal:** Extend the completed provider plugin architecture with first-class provider packs for major vendors so the coding agent can work more like Claude Code, Codex, OpenCode, and similar tools without redesigning the LangGraph runtime or the provider seam.

This phase is the provider-focused follow-on to Phase 12.

## Why This Is A Separate Phase

Phase 12 completed the architectural seam:

- `AgentBackendProvider` already defines the core provider contract
- `BackendProviderPlugin` already allows plug-and-play runtime providers
- the built-in provider registry already merges built-ins and plugin-discovered providers

What remains is product parity, not architecture replacement:

- first-class OpenAI provider support instead of relying only on the generic OpenAI-compatible path
- first-class Anthropic support with provider-specific transport and capability reporting
- first-class OpenRouter support with provider-specific defaults and discovery/probe behavior
- a documented plugin-first path for emerging providers such as Zen and future vendors
- explicit capability follow-on work for streaming, structured outputs, vision, model discovery, and provider-specific parameters where the current backend contract does not yet expose them

## Current State Summary

### Already In Place

- `beep/agent/provider_contracts.py` defines `AgentBackendProvider`
- `beep/plugins/contracts.py` defines `BackendProviderPlugin`
- `beep/agent/provider_plugins.py` already loads built-in providers and plugin providers together
- the backend request seam now has compatibility-preserving request fields for future streaming, `response_format`, and provider-specific option forwarding without breaking older plugin backends
- the built-in Beep, OpenAI-compatible, and Anthropic autonomous-agent backends now consume real streamed provider deltas end to end through the LangGraph runtime
- selected provider-specific options are now surfaced through config, CLI, runtime forwarding, and provider status output:
   - OpenAI-style reasoning effort
   - OpenAI-style parallel tool-calls override
   - Anthropic thinking budget
- the OpenAI-style and Beep autonomous-agent paths now forward `response_format` through the backend/client contract instead of documenting structured output as a missing transport capability
- multimodal user content is now preserved through the agent message adapter, and the Anthropic adapter now normalizes OpenAI-style `image_url` blocks into Anthropic image blocks for base64 data URLs
- the public `run_agent`, `resume_agent`, and LangGraph execution surfaces now accept `response_format`, and the initial run surface now accepts richer multimodal user content without bypassing the existing provider seam
- the public `beep agent` CLI surface now exposes `--response-json`, `--response-schema`, `--input-file`, and `--input-image`, mapping those flags onto the existing `response_format` and initial multimodal user-content contracts without creating a parallel provider path
- the broader provider-parameter audit is now explicit: the current public autonomous-agent config surface only models reasoning effort, parallel tool calls, and Anthropic thinking budget, so additional provider-specific knobs require a future config and backend-contract addition instead of hidden pass-through behavior
- built-in providers already exist for:
   - Anthropic hosted Messages API provider
  - Beep.AI.Server
   - first-class OpenAI hosted API provider
  - generic OpenAI-compatible endpoints
  - LM Studio
  - Ollama
- provider-aware CLI discovery and configuration already exist through `beep agent providers`, `beep agent configure`, and `beep agent status`

### Gaps To Close

1. **OpenAI parity is started but not finished.**
   A first-class OpenAI provider pack now exists with hosted defaults, provider-specific guidance, real streamed completion support, and selected provider-specific options, but structured outputs and richer capability work still belong to follow-on items in this phase.

2. **Anthropic parity is started but not finished.**
   A first-class Anthropic provider pack now exists with a dedicated Messages API backend, provider-specific validation, real streamed completion support, and a surfaced thinking-budget control, but structured outputs and richer Anthropic-specific capability work still belong to follow-on items in this phase.

3. **OpenRouter parity is started but not finished.**
   A first-class OpenRouter provider pack now exists on top of the OpenAI-compatible seam, including support for path-prefixed `/api/v1` transports, provider-specific guidance, streamed completion support through the shared OpenAI-compatible backend, and focused tests, but richer OpenRouter-specific routing metadata still belongs to follow-on items in this phase.

4. **Emerging providers such as Zen need a documented entry path.**
   The provider seam is already plug-and-play, but the roadmap needs a stable plugin-first policy for providers whose contracts are still moving.

5. **Provider capability parity now has a clear boundary.**
   Richer model discovery and any future provider-specific settings beyond the currently modeled controls should be tracked as explicit follow-on contract work rather than implied by provider registration.

## Architectural Direction

### Keep The Existing Provider Seam

This phase must build on the existing provider architecture instead of replacing it.

Use:

- `AgentBackendProvider` for built-in provider packs
- `BackendProviderPlugin` for plugin-authored providers
- `provider_plugins.py` and `provider_registry.py` as the single provider-discovery path

Do **not** add provider-specific branching into the graph runtime.

### First-Class Providers Versus Plugin-First Providers

The roadmap distinguishes between:

- **first-class built-in provider packs** for stable, widely used providers that deserve supported defaults, docs, probes, and tests
- **plugin-first provider packs** for emerging or less stable integrations where Beep.AI.Code should provide the extension seam and templates before adopting them as built-ins

### Capability Parity Must Be Explicit

Adding a provider class is not enough.

Each provider pack should state the current support level for:

- chat completion
- tool calling
- streaming
- structured output
- vision
- model discovery or probe behavior
- provider-specific settings that materially affect agent behavior

If a capability requires a contract extension in `beep/agent/backends.py`, that extension must be tracked as a separate todo item in this phase rather than hidden inside provider implementations.

## Workstreams

### A. First-Class OpenAI Provider Pack

**Objective:** Add a named built-in OpenAI provider so users do not need to treat OpenAI as only a generic compatible endpoint.

- add a built-in provider pack with OpenAI-specific defaults and guidance
- support provider-aware probe/model discovery behavior where the public API allows it
- keep transport code aligned with the existing backend seam instead of special-casing the graph runtime

### B. First-Class Anthropic Provider Pack

**Objective:** Add a built-in Anthropic provider with explicit capability reporting and a clean backend adapter.

- add provider class and any required backend adapter
- align configuration guidance with Anthropic-specific auth and model selection
- expose capability notes honestly when streaming or other features are not yet wired end-to-end

### C. First-Class OpenRouter Provider Pack

**Objective:** Add a built-in OpenRouter provider with provider-specific defaults, probes, and model-listing behavior.

- use the OpenAI-compatible transport seam where appropriate
- add OpenRouter-specific default base URL and any provider-required headers or discovery behavior
- keep model-routing and provider-specific metadata explicit in guidance and tests

### D. Plugin-First Community Provider Path

**Objective:** Make it easy to add providers such as Zen without waiting for built-in adoption.

- document the provider-pack authoring workflow
- add or improve a provider plugin template/example
- treat Zen as plugin-first until its API, auth, and model-discovery contract are stable enough for built-in support

### E. Capability Follow-On Work

**Objective:** Track feature parity work that goes beyond simple provider registration.

- extend the backend contract only where needed for real capabilities such as streaming
- define capability reporting expectations for structured outputs, vision, and richer provider parameters
- avoid expanding capability claims ahead of the actual backend/runtime support

### F. Provider UX, Docs, And Tests

**Objective:** Keep provider setup and runtime diagnostics aligned with the registry.

- update provider CLI guidance surfaces
- ensure provider probes and model discovery show useful operator feedback
- add focused unit and integration tests per provider pack

## Todo Tracker

### A. OpenAI Provider Pack

- [x] Add a built-in OpenAI provider class and register it through the existing provider registry.
- [x] Add OpenAI-specific guidance and probe behavior to `beep agent providers`, `beep agent configure`, and `beep agent status`.
- [x] Add focused tests for provider selection, configuration validation, and backend construction.

### B. Anthropic Provider Pack

- [x] Add an Anthropic provider class and any required backend adapter.
- [x] Add Anthropic-specific configuration guidance and probe behavior.
- [x] Add focused tests for payload building, configuration validation, and capability reporting.

### C. OpenRouter Provider Pack

- [x] Add an OpenRouter provider class using the existing provider seam.
- [x] Add provider-specific base URL, guidance, and model discovery or probe behavior.
- [x] Add focused tests for configuration validation, provider selection, and capability reporting.

### D. Plugin-First Vendor Path

- [x] Add or improve a provider plugin template/example for third-party providers.
- [x] Document the plugin-first path for Zen and similar providers.
- [x] Add a regression test proving plugin-provided backend providers appear in the provider registry and CLI guidance.

### E. Capability Parity Follow-On

- [x] Audit the current backend contract for streaming requirements and implement the minimum changes needed for real provider streaming support.
- [x] Audit and implement the minimum backend-contract changes needed for structured-output forwarding on OpenAI-style transports and the canonical Beep backend.
- [x] Audit and implement the minimum backend-contract changes needed to preserve multimodal vision inputs and normalize Anthropic image blocks from OpenAI-style `image_url` messages.
- [x] Audit remaining provider-specific parameter forwarding beyond the selected reasoning, parallel tool-call, and Anthropic thinking controls already exposed.
- [x] Add explicit capability notes instead of implicit parity assumptions where support is still partial.

### F. Docs And Validation

- [x] Update roadmap and user-facing docs so built-in versus plugin-first provider policy is clear.
- [x] Add focused tests for `beep agent providers`, `beep agent configure`, and `beep agent status` with the new providers.
- [x] Add smoke coverage for Beep, OpenAI, Anthropic, and OpenRouter selection paths.

## Primary Files

- `beep/agent/provider_contracts.py`
- `beep/agent/provider_plugins.py`
- `beep/agent/provider_registry.py`
- `beep/agent/provider_base.py`
- `beep/agent/backends.py`
- `beep/plugins/contracts.py`
- `beep/commands/agent.py`
- `tests/` provider and CLI coverage for autonomous-agent configuration

## Acceptance Criteria

1. Beep.AI.Code ships first-class built-in provider packs for OpenAI, Anthropic, and OpenRouter.
2. The provider registry remains the single discovery and selection path for built-in and plugin-provided providers.
3. Provider capability reporting is explicit and honest for streaming, structured output, vision, and similar features.
4. Zen and other emerging providers have a documented plugin-first path even when they are not built in yet.
5. Provider CLI guidance and focused test coverage are updated together with each provider pack.

## Completion Note

Phase 16 is complete. The remaining provider-specific work now belongs to later phases only when new config fields and backend-contract extensions are intentionally introduced.

## Out Of Scope For This Phase

- redesigning the LangGraph runtime or tool orchestration
- replacing the existing provider plugin architecture
- introducing a portable agent bundle or publishing workflow
- making npm or any other packaging channel the core provider architecture