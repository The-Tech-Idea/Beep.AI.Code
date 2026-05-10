# Phase 18 — Publishing Channels And Deployment Targets

**Goal:** Add multi-channel publishing and deployment adapters for portable coding-agent bundles, treating npm as one supported channel among several rather than the canonical runtime or artifact model.

This phase depends on the portable-bundle contract from Phase 17.

## Why This Is A Separate Phase

Phase 14 already covered packaging and upgrades for the main Beep.AI.Code CLI.
Phase 17 defines the portable bundle.

What still remains is the adapter layer that takes that bundle and publishes or deploys it through different channels:

- npm package publication
- wheel- or `pipx`-friendly runner packaging where appropriate
- GitHub release assets
- container image publication
- Beep.AI.Server registration or hosted deployment

This phase keeps channel-specific mechanics separate from the canonical bundle model.

## Architectural Direction

### One Bundle, Many Adapters

The portable bundle from Phase 17 is the only canonical artifact.

Each channel adapter should:

- consume the same bundle metadata
- add only the wrapper files and release metadata that the target channel requires
- avoid redefining agent semantics independently per channel

### Publishing Taxonomy

This phase should keep three different concerns separate:

1. **Local packaging**
   Build the bundle and any local wrapper artifacts.

2. **Registry publishing**
   Publish to npm, GitHub releases, package indexes, or container registries.

3. **Runtime deployment**
   Register or deploy the bundle to a target runtime such as Beep.AI.Server.

### npm Is One Channel

npm support is important, but it must stay in the correct place:

- npm is a publish and distribution channel
- Node-based runners are one deployment target family
- the portable bundle remains channel-neutral

## Current State Summary

### Already In Place

- the Beep.AI.Code CLI has its own packaging and upgrade lifecycle from Phase 14
- the Beep.AI.Server JavaScript SDK already has a package manifest and basic TypeScript build scripts
- Beep.AI.Server already exposes agent-definition and orchestration concepts that can become a hosted deployment target
- Beep.AI.Code now has local packaging adapters under `beep/publishing/` plus a `beep agent package <bundle_file_or_id>` command for dry-run or on-disk packaging of supported channel wrappers
- the first packaging slice now generates deterministic npm and Python wrapper skeletons that embed the same portable bundle payload and preserve shared metadata
- focused packaging tests now cover dry-run behavior, fixture-backed output generation, and metadata parity across npm and Python local wrappers
- the packaging adapter layer now also generates deterministic GitHub release asset layouts and container wrapper skeletons from the same portable bundle payload
- focused packaging tests now cover dry-run behavior and fixture-backed outputs for GitHub release and container channels in addition to npm and Python wrappers
- Beep.AI.Code now has a hosted deployment adapter through `beep agent deploy <bundle_file_or_id>`, backed by the existing Beep.AI.Server token-auth portable bundle import endpoint from Phase 17
- focused deployment tests now cover dry-run deployment planning, API client bundle-import request shaping, missing-token guardrails, and live deploy command behavior against the existing server import contract
- all supported local packaging channels now emit a shared `release-metadata.json` artifact built from the same bundle provenance, compatibility envelope, release tag, and runner metadata that the hosted Beep.AI.Server deployment plan now exposes directly
- the README and CI workflow now treat package and deploy dry-run validation as an explicit no-credentials release gate instead of an implicit side effect of the broader test suite

### Gaps To Close

All planned Phase 18 gaps are now closed for the scope of this phase.

Future follow-on work belongs to later phases rather than reopening this one:

1. remote publication automation for registries or package indexes
2. richer hosted deployment lifecycle feedback after bundle registration

## Workstreams

### A. Local Packaging And Dry-Run Validation

**Objective:** Make it possible to build channel-ready artifacts locally before touching remote registries or runtimes.

- add local packaging flows for channel adapters
- add dry-run validation for each adapter
- make artifact inspection and failure modes visible before remote publishing

### B. npm Adapter

**Objective:** Support npm as one publish channel for portable agent bundles.

- define how the portable bundle is wrapped for Node-based consumption
- define package metadata, versioning, and release validation expectations
- align with the JavaScript SDK dependency lane from Phase 17

### C. Python-Oriented Runner Adapter

**Objective:** Support wheel- or `pipx`-friendly packaging where a Python runner is the desired consumption model.

- define when a Python runner wrapper is appropriate
- keep the runner wrapper separate from the main Beep.AI.Code CLI package lifecycle
- validate that the wrapper consumes the same portable bundle metadata as other channels

### D. GitHub Release And Container Adapters

**Objective:** Support repository and container-oriented distribution workflows.

- define GitHub release asset generation from the portable bundle
- define container packaging expectations using the same canonical bundle
- add dry-run validation for release and container metadata

### E. Beep.AI.Server Deployment Adapter

**Objective:** Treat Beep.AI.Server as a first-class hosted deployment target for portable agent bundles.

- define bundle-to-server registration or deployment semantics
- keep server-specific deployment metadata explicit
- align deployment flows with the import/export contract from Phase 17

### F. Provenance, Docs, And CI

**Objective:** Make publishing repeatable and auditable.

- define provenance expectations shared by all channel adapters
- add dry-run or fixture-based validation for channel metadata
- keep docs aligned with what is actually supported and automated

## Todo Tracker

### A. Packaging And Dry-Run Validation

- [x] Add channel-adapter dry-run flows for local packaging.
- [x] Add validation that each adapter consumes the same portable bundle metadata.
- [x] Add fixture-based tests for local packaging outputs.

### B. npm Channel

- [x] Define the npm wrapper format for portable bundles.
- [x] Define package metadata and release validation expectations.
- [x] Add dry-run or fixture-based npm packaging tests.

### C. Python Runner Channel

- [x] Define the Python-runner wrapper contract for portable bundles.
- [x] Add local packaging and dry-run validation for the Python-oriented wrapper.
- [x] Add tests proving the wrapper uses the same bundle semantics as the npm adapter.

### D. GitHub Release And Container Channels

- [x] Define release asset generation from the portable bundle.
- [x] Define container wrapper and metadata generation from the same bundle.
- [x] Add dry-run validation for GitHub release and container packaging flows.

### E. Beep.AI.Server Deployment Channel

- [x] Define the hosted deployment or registration flow for portable bundles.
- [x] Record the required Beep.AI.Server endpoint and contract work explicitly.
- [x] Add contract tests or fixtures for bundle-to-server deployment metadata.

### F. Provenance And Documentation

- [x] Define shared provenance fields and release metadata expectations across channels.
- [x] Update docs to show npm as one supported channel among several.
- [x] Add CI planning for dry-run publish validation without requiring live credentials in every test path.

## Cross-Repo Dependency Lane

### Beep.AI.Server Dependencies

- hosted deployment or registration endpoints for portable bundles
- compatibility rules for imported bundle metadata
- deployment status and lifecycle feedback expected by the publishing adapter

### JavaScript SDK Dependencies

- npm-ready build and packaging hardening
- client helpers for hosted deployment or bundle import/export workflows where applicable

## Primary Files

- `beep/publishing/channel_adapters.py`
- `beep/publishing/release_container_support.py`
- `beep/publishing/release_metadata.py`
- `beep/publishing/server_deploy_support.py`
- `beep/commands/agent_deploy.py`
- `beep/api/client_agent_bundle_support.py`
- `beep/commands/agent_package.py`
- `README.md`
- `.github/workflows/beep-ai-code-ci.yml`
- `Beep.AI.Server/Beep.AI.SDK/JavaScript/package.json`
- `Beep.AI.Server/Beep.AI.SDK/JavaScript/src/client.ts`
- future Beep.AI.Server agent deployment and import/export surfaces

## Completion Note

Phase 18 is now complete:

- `beep agent package <bundle_file_or_id>` now validates a portable bundle, builds local channel package plans, supports `--dry-run`, and can write packaging outputs under a chosen output root
- `beep/publishing/channel_adapters.py` now owns the shared packaging contract so npm and Python wrappers consume the same bundle version, description, bundle filename, and embedded manifest payload
- the npm adapter now emits a deterministic `package.json`, `index.cjs`, `README.md`, and embedded bundle file for local inspection and later publish automation
- the Python adapter now emits a deterministic `pyproject.toml`, package module, `README.md`, and embedded bundle resource for local inspection and later publish automation
- `beep/publishing/release_container_support.py` now emits deterministic GitHub release metadata, release notes, checksum placeholders, container Dockerfiles, entrypoints, and wrapper READMEs from the same canonical bundle metadata
- fixture-backed tests now pin the generated outputs and assert metadata parity across npm, Python, GitHub release, and container local wrappers
- `beep agent deploy <bundle_file_or_id>` now supports a dry-run Beep.AI.Server deployment plan plus live registration through `/ai-middleware/api/agents/bundles/import`
- `beep/publishing/server_deploy_support.py` now makes the server-specific deployment metadata explicit by recording the endpoint path, declared runner kinds, expected execution target, and server-compatibility warnings in a reusable plan structure
- `beep/api/client_agent_bundle_support.py` now exposes a typed `import_agent_bundle()` helper so the deployment command reuses the same explicit server contract rather than building ad hoc requests inline
- focused deployment tests now pin a fixture-backed local deployment plan and validate the live deploy command against the existing bundle import API seam
- `beep/publishing/release_metadata.py` now defines one shared provenance and release metadata contract that all local packaging channels emit as `release-metadata.json` and that hosted deployment plans expose directly
- the README now documents package and deploy channels together, explicitly treating npm as one supported distribution channel among several rather than the canonical runtime model
- the CI workflow now runs focused package and deploy dry-run tests as an explicit no-credentials release gate

## Acceptance Criteria

1. The roadmap defines multi-channel publishing and deployment on top of the Phase 17 portable bundle rather than inventing per-channel agent formats.
2. npm is documented and planned as one supported channel, not the canonical runtime model.
3. The publishing taxonomy separates local packaging, registry publication, and hosted deployment.
4. Each planned adapter is validated through dry-run or fixture-based checks before live publishing is assumed.
5. Cross-repo dependencies for hosted deployment and npm readiness remain explicit in the roadmap.

## Out Of Scope For This Phase

- defining the portable bundle contract itself
- rewriting the Beep.AI.Code CLI install/update lifecycle from Phase 14
- treating npm as the only supported distribution path
- redesigning provider/runtime behavior that belongs to earlier phases