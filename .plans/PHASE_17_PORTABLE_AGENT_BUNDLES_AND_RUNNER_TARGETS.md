# Phase 17 — Portable Agent Bundles And Runner Targets

**Goal:** Define one canonical portable agent bundle and the export/import/run flows around it so Beep.AI.Code agents can move between local execution, Beep.AI.Server-backed execution, and future publish channels without making npm, Python packaging, or containerization the canonical artifact.

This phase follows the provider-pack work in Phase 16 and uses the completed packaging and parity phases as its baseline.

## Why This Is A Separate Phase

Phase 14 solved packaging for the **Beep.AI.Code CLI itself** and for the managed autonomous-agent runtime.
It did **not** define a portable agent artifact.

Phase 15 solved coding-agent runtime parity features such as planning, sub-agents, streaming events, and verification.
It did **not** define how an agent is exported, imported, versioned, shared, or run outside the current local CLI flow.

This phase isolates the missing artifact and runner contract:

- how an agent definition is represented as a portable bundle
- how the CLI exports and imports that bundle
- how local and hosted runners consume the same bundle
- how Beep.AI.Server and the JavaScript SDK align with that contract

## Current State Summary

### Already In Place

- Beep.AI.Code has a managed local autonomous-agent runtime and the `beep agent ...` command family
- Beep.AI.Server already has an `AgentDefinition` contract plus CRUD and resolve routes for stored agent definitions
- the JavaScript SDK already exposes agent orchestration methods such as plan and execute
- provider selection, tool policy, MCP references, and system prompts already exist as conceptual inputs to an agent definition
- `beep/agent/bundle_contract.py` now defines a versioned portable bundle manifest with explicit compatibility, runtime, provenance, and asset-disposition sections so export/import work can build on a stable local contract instead of ad hoc JSON
- focused bundle-contract tests now cover round-trip serialization, server-shape alignment for core agent fields, asset validation, and local CLI compatibility checks
- `beep/agent/bundle_store.py` now builds portable bundles from the active autonomous-agent config, writes normalized bundle JSON, and installs imported bundles into the local library under `~/.beepai/agent-bundles/`
- `beep agent export ...` and `beep agent import ...` now exist on the main autonomous-agent command surface, including compatibility validation on import and round-trip CLI coverage
- `beep agent run <bundle_file_or_id> <goal>` now resolves an installed or file-backed portable bundle, validates local-runner compatibility, rehydrates a local runtime config, and executes through the existing `run_agent()` flow with bundle-aware tool-policy and prompt handling

### Final Hardening Completed

1. **Local and hosted runner alignment is now explicit for this phase.**
   Phase 17 now covers the local CLI runner plus the Beep.AI.Server bundle interop seam; broader publish and deployment targets move to Phase 18.

2. **Cross-repo alignment is now in place.**
   Beep.AI.Code, Beep.AI.Server, and the JavaScript SDK now share the portable bundle contract shape needed for import/export lifecycle parity.

3. **Deterministic validation and provenance hardening are now covered.**
   The bundle contract now has an explicit payload validation entrypoint, deterministic fixture-backed export coverage, stronger compatibility mismatch tests, and initial provenance signature placeholders.

## Architectural Direction

### The Bundle Is Canonical

The portable bundle must be the canonical artifact.

All of these should consume the same agent bundle contract:

- local CLI runner
- Beep.AI.Server registration or import
- npm package wrapper
- wheel-based or `pipx`-friendly runner wrapper
- GitHub release asset packaging
- container image packaging

### The Bundle Must Be Provider-Agnostic

The bundle should describe:

- agent metadata and version
- provider and model selection
- tool policy and MCP references
- prompts, rules, and any included assets
- runtime requirements and compatibility metadata
- publishing metadata such as publisher, channel annotations, and provenance fields

The bundle must not assume:

- Python-only execution
- npm-only execution
- Beep.AI.Server-only hosting

### Reuse Existing Semantics Where Possible

The portable bundle should align conceptually with the existing Beep.AI.Server shapes:

- `AgentDefinition`
- `AgentModelConfig`
- `AgentToolPolicy`

But the bundle contract should remain explicitly versioned and independent so Beep.AI.Code can validate compatibility even when server-side contracts evolve.

## Workstreams

### A. Bundle Schema And Versioning

**Objective:** Define a versioned portable agent bundle format and compatibility policy.

- define the bundle manifest structure
- define version, schema, compatibility, and provenance fields
- decide which resources are embedded versus referenced

### B. Export And Import CLI Flows

**Objective:** Add operator-facing CLI commands for moving agents in and out of the portable bundle format.

- add export flows for agent definitions and runtime metadata
- add import flows with compatibility validation
- add round-trip validation expectations and failure modes

### C. Local Runner Targets

**Objective:** Make portable bundles executable through a local runner flow in Beep.AI.Code.

- define runner target metadata for local execution
- add `beep agent run` or equivalent portable-bundle execution flow
- ensure provider configuration and tool policy are respected when running imported bundles

### D. Beep.AI.Server Interop

**Objective:** Make the portable bundle compatible with Beep.AI.Server registration and hosted execution.

- map bundle fields to the server-side agent-definition semantics
- define import/export expectations across the server API and resolver layer
- keep server-specific fields explicit instead of leaking them into the generic local-only format

### E. JavaScript SDK And Cross-Repo Contract Lane

**Objective:** Keep Beep.AI.Code honest about the work that cannot be finished in this repo alone.

- define the server-side contract changes needed for import/export support
- define the JavaScript SDK changes needed for parity with the bundle lifecycle
- keep blockers and dependencies explicit in this phase instead of burying them in later publish work

### F. Provenance, Validation, And Tests

**Objective:** Ensure portable bundles are deterministic, testable, and safe to consume.

- add schema validation and round-trip tests
- add compatibility checks for version mismatches
- define provenance and signature placeholders even if signing is phased later

## Todo Tracker

### A. Bundle Contract

- [x] Define the portable bundle manifest, schema version, and compatibility policy.
- [x] Define which agent assets are embedded, referenced, or generated at import time.
- [x] Define provenance metadata fields needed by later publishing channels.

### B. CLI Export And Import

- [x] Add a `beep agent export` flow for portable bundle generation.
- [x] Add a `beep agent import` flow with compatibility validation.
- [x] Add round-trip tests proving exported bundles can be imported without losing supported semantics.

### C. Bundle Execution

- [x] Add a portable-bundle runner target for local execution.
- [x] Add CLI UX for selecting or validating execution targets when running imported bundles.
- [x] Add smoke tests proving imported bundles can run through the local agent flow.

### D. Beep.AI.Server Interop

- [x] Define the mapping between the portable bundle and Beep.AI.Server agent definitions.
- [x] Define the required server-side import/export endpoints and compatibility rules.
- [x] Add contract tests or fixtures that validate bundle-to-server mapping behavior.

### E. JavaScript SDK And Cross-Repo Dependencies

- [x] Define the JavaScript SDK import/export helpers needed for agent-bundle lifecycle parity.
- [x] Record the required Beep.AI.Server contract changes as explicit blockers or prerequisites.
- [x] Keep PH-17 deliverables split between Beep.AI.Code-only work and cross-repo follow-on tasks.

### F. Validation And Provenance

- [x] Add schema validation and bundle compatibility tests.
- [x] Add deterministic export expectations and fixture coverage.
- [x] Define initial provenance fields and later signing hooks without blocking the base bundle format.

## Cross-Repo Dependency Lane

### Required Beep.AI.Server Follow-On Work

- completed in this slice: preserve export-friendly model metadata (`base_url`, `provider_options`) plus native-framework compatibility in the server-side agent-definition contract
- completed in this slice: add token-auth portable bundle import/export endpoints under `/ai-middleware/api/agents/*`
- completed in this slice: add explicit server-contract compatibility mapping and focused bundle-to-server interop tests/fixtures

### Required JavaScript SDK Follow-On Work

- completed in this slice: extend `Beep.AI.SDK/JavaScript/src/client.ts` with typed bundle import/export helpers aligned to `/ai-middleware/api/agents/*`
- completed in this slice: add portable bundle interfaces to `Beep.AI.SDK/JavaScript/src/types.ts` so bundle lifecycle responses are first-class SDK types
- completed in this slice: harden `Beep.AI.SDK/JavaScript/package.json` with an explicit export map, publish metadata, and TypeScript-based build/check scripts that do not reference missing Jest/ESLint tooling

These cross-repo items are now in place, and the validation/provenance lane is complete. Phase 18 now owns the publish-channel follow-on work.

## Primary Files

- `beep/agent/bundle_contract.py`
- `beep/agent/bundle_store.py`
- `beep/agent/loop.py`
- `beep/agent/tools/factory.py`
- `beep/commands/agent_bundle.py`
- `beep/cli.py`
- `beep/cli_support.py`
- `Beep.AI.Server/app/services/utils/agent_definition_contracts.py`
- `Beep.AI.Server/app/services/utils/agent_portable_bundle_service.py`
- `Beep.AI.Server/app/routes/ai_middleware/agent_bundles.py`
- `Beep.AI.Server/tests/test_agent_bundle_interop.py`
- `Beep.AI.Server/Beep.AI.SDK/JavaScript/src/client.ts`
- `Beep.AI.Server/Beep.AI.SDK/JavaScript/package.json`

## Current Slice Note

The Phase 17 contract slice is now complete in Beep.AI.Code. The canonical local manifest includes:

- `kind` + `schema_version` for versioned contract identification
- core agent fields aligned to existing server semantics (`model`, `tool_policy`, MCP and data-source references, tags, metadata)
- explicit `compatibility` rules for supported CLI versions plus placeholder cross-repo contract-version lanes
- explicit `runtime` requirements for Python/runtime expectations and supported runner kinds
- explicit `assets` with `embedded`, `referenced`, and `generated` dispositions
- explicit `provenance` fields for authoring tool/version, source repo/revision, publisher, publish-channel annotations, and optional signature placeholders

The Phase 17 export/import slice is now also in place for local CLI use:

- `beep agent export <agent_id>` builds a portable bundle from the active autonomous-agent configuration without exporting API keys
- `beep agent import <bundle_file>` validates bundle compatibility for the current CLI and installs a normalized copy into the local bundle library
- focused round-trip tests prove that exported bundles can be imported without losing the supported semantics currently modeled by the bundle contract

The Phase 17 local runner slice is now also in place:

- `beep agent run <bundle_file_or_id> <goal>` executes a supported imported bundle through the existing local LangGraph agent runtime instead of introducing a second runner stack
- local execution validates that the bundle declares the `local` runner target and that any referenced MCP servers are available on the current machine
- bundle execution now forwards bundle-owned provider options, merges the bundle system prompt with the workspace prompt, and applies bundle tool-policy constraints before the graph runs
- focused runtime and CLI smoke tests prove that installed bundles can run through the local flow and fail clearly when local MCP requirements are missing

The Phase 17 Beep.AI.Server interop slice is now also in place:

- the server-side `AgentDefinition` contract now preserves export-relevant model metadata such as `base_url` and `provider_options`, and its validation layer now accepts the documented `native` framework
- `app/services/utils/agent_portable_bundle_service.py` now owns bundle-to-server mapping, server contract compatibility checks, and import/export shaping instead of scattering that logic through routes
- token-auth import/export endpoints now exist under `/ai-middleware/api/agents/definitions/<agent_id>/bundle` and `/ai-middleware/api/agents/bundles/import`
- focused server interop tests cover contract round-tripping, server compatibility rules, and the new middleware endpoint seam

The Phase 17 JavaScript SDK parity slice is now also in place:

- `Beep.AI.SDK/JavaScript/src/client.ts` now exposes typed `exportAgentBundle()` and `importAgentBundle()` helpers against the token-auth middleware endpoints
- `Beep.AI.SDK/JavaScript/src/types.ts` now includes portable bundle manifest, compatibility, runtime, provenance, asset, and import/export response interfaces so the SDK can model the same contract already enforced in Beep.AI.Code and Beep.AI.Server
- `Beep.AI.SDK/JavaScript/package.json` now exposes an explicit publish/export surface and replaces stale Jest/ESLint script references with TypeScript-based `build`, `check`, `test`, and `prepack` scripts suitable for this package's current toolchain

The Phase 17 validation and provenance hardening slice is now also in place:

- `beep/agent/bundle_contract.py` now exposes an explicit bundle-payload validation entrypoint, validates ISO-8601 provenance timestamps, and supports optional provenance signature placeholders without making signing mandatory
- deterministic fixture-backed CLI export coverage now locks the canonical JSON shape when the export timestamp is fixed, so future contract changes surface clearly in review
- compatibility coverage now includes both minimum and maximum CLI-version mismatch checks, and Beep.AI.Server plus the JavaScript SDK preserve the optional provenance signature shape in their shared bundle surfaces

## Acceptance Criteria

1. Beep.AI.Code defines one explicit portable agent bundle contract with schema versioning and compatibility rules.
2. The CLI can export and import portable bundles with focused validation and round-trip coverage.
3. The local runner can execute a supported imported bundle without requiring the original authoring environment.
4. Beep.AI.Server and the JavaScript SDK dependency lane is written explicitly in the phase and not hidden behind local-only assumptions.
5. The bundle contract is channel-neutral and does not assume npm, Python packaging, or containers as the canonical artifact.

## Out Of Scope For This Phase

- final multi-channel publish commands
- registry publishing workflows such as npm release automation
- replacing the existing Beep.AI.Code CLI packaging strategy
- redesigning the provider architecture established in Phase 12 and extended in Phase 16