# Phase 14 — Packaging, Distribution, And Update Lifecycle

**Goal:** Make installation, upgrades, and release artifacts predictable for both the main `beep` CLI package and the managed `~/.beepai/agents_env` runtime.

This phase starts after the core runtime and product-parity workstreams are structurally in place. It focuses on how the product is installed, upgraded, versioned, repaired, and released.

## Why This Is A Separate Phase

The product already has the raw building blocks for distribution:

- a standard Python package in `pyproject.toml`
- a `beep` console entry point
- documented editable, `pipx`, and Git-based install paths in `README.md`
- built artifacts under `dist/`
- a separate managed agent runtime provisioned by `agent/environment.py`

What is still missing is the policy and operational layer around those pieces:

- which install channels are actually supported for end users versus contributors
- how upgrades are communicated and performed
- how the CLI version relates to the managed agent-runtime version
- when migrations run and what recovery path exists if they fail
- what release validations must pass before publishing artifacts

This phase supersedes the older packaging bullets in `MASTER-TODO-TRACKER.md` Phase 7 so the active plan set has one canonical packaging roadmap.

## Current State Summary

### Already In Place

- `pyproject.toml` builds a normal wheel/sdist package
- `README.md` now documents primary install paths, recommends `pipx` as the current end-user path, explicitly classifies install-channel support levels, and states the supported Python/runtime assumptions
- `completions/beep.bash` exists and is documented
- `.github/workflows/beep-ai-code-ci.yml` now validates focused agent-runtime tests, Ruff lint, wheel/sdist builds, generates a `SHA256SUMS.txt` manifest for release artifacts, runs `twine check` against wheel and sdist outputs, and exercises fresh-venv, `pipx`, and upgrade smoke paths
- `beep/config.py` now stamps `code.json` with a schema version and migrates legacy config payloads on load
- `beep/sessions/history.py` now stamps session-history files with a schema marker, migrates legacy JSONL histories in place on read/list/search, and treats newer unsupported history schemas as invalid for the current CLI
- `beep/memory/agent.py` now persists `.beep/session_memory.json` with a schema version and rewrites legacy dict payloads on load
- `beep/agent/environment.py` can create, reinstall, and remove a managed autonomous-agent runtime
- `beep/agent/environment_catalog.py` defines the managed package catalog for that runtime
- `AgentEnvironmentManager.status()` now reports a compatibility stamp/state for the managed runtime, and `beep agent status` renders that state for operators
- `beep agent setup` now preserves an already-current managed runtime and refreshes stale, incomplete, or missing runtimes instead of blindly reinstalling every time
- `beep agent status` now also surfaces a concrete repair command, and the runtime distinguishes normal refresh via `beep agent setup` from full rebuild via `beep agent reinstall runtime`
- Interrupted or partial managed-runtime installs now resolve to an explicit rebuild contract: `beep agent setup` fails fast with reinstall guidance, and `beep agent reinstall runtime` is the canonical recovery path for indeterminate runtime state
- `beep diagnostics` now includes a doctor-style repair summary for config schema, managed runtime, session history, and workspace session memory, and `beep doctor` is now a first-class alias for that in-product upgrade and repair surface
- `beep doctor --fix` now auto-applies the supported managed-runtime repair flow when the doctor output recommends `beep agent setup` or `beep agent reinstall runtime`, while still failing closed for manual-only repair cases
- `beep self-update` now provides a channel-aware in-product upgrade workflow for supported install types by inspecting installed distribution metadata and either executing or printing the correct update steps
- `README.md` now defines the deprecation and breaking-change communication contract for releases, including when release notes must call out removals, migration steps, and post-upgrade repair commands
- `tools/ci/generate_release_checksums.py` now defines the release checksum manifest contract for built wheel and sdist artifacts, and the README release checklist now treats that manifest as part of the expected release bundle

### Still Missing

1. **Distribution policy is still only partially explicit.**
   Install-channel support and Python-version expectations are now documented, but publication expectations across PyPI and any future OS-native channels are still unresolved.

2. **Some channel-specific update limitations remain.**
   The repo now has a one-command `beep self-update` workflow for supported install channels, but installs from local artifact paths still require manual reinstall from a newer wheel or sdist.

3. **CLI and managed-runtime compatibility enforcement is still only partially complete.**
   The autonomous-agent environment now records compatibility, blocks stale runtimes at startup, distinguishes refresh versus rebuild repair commands, and supports `beep doctor --fix` for the narrow managed-runtime auto-repair path, but broader guided upgrades and non-runtime automatic repair flows are still missing.

4. **Broader cache invalidation policy is still only partially defined.**
   Main CLI config files and local session-state files now have explicit migration rules, but future non-session cache directories still need the same schema-or-invalidate policy.

5. **Release validation is still incomplete.**
   The repo now validates build artifacts plus wheel, `pipx`, and upgrade smoke paths in CI, and the release checklist is now maintained in active README documentation, but broader release automation is still incomplete.

## Workstreams

### A. Canonical Install Channels

**Objective:** Define and document which install paths are first-class for which audiences.

- Classify install paths into contributor, early-adopter, and end-user channels.
- Decide whether `pipx` is the primary end-user recommendation for now.
- Document the support level for editable installs, local wheel installs, and Git-based installs.
- Clarify prerequisites such as supported Python versions and virtual-environment expectations.

### B. Artifact Strategy And Distribution Channels

**Objective:** Define what gets built and where it is published.

- Treat wheel and sdist artifacts as the minimum required release outputs.
- Decide when PyPI publishing becomes the canonical public channel.
- Decide whether OS-native channels such as Homebrew, winget, Scoop, or standalone binaries belong in this repo's near-term roadmap or remain future work.
- Define artifact naming, integrity checks, and release-note expectations.

### C. Main CLI Upgrade UX

**Objective:** Make upgrading the `beep` package understandable and repeatable.

- Document canonical upgrade commands for `pip`, `pipx`, and Git-based installs.
- Provide a `beep self-update` entrypoint that can execute the detected upgrade path when the install source is reproducible.
- Use `beep doctor` / `beep diagnostics` as the in-product repair helper for upgrade verification and recovery guidance, with `beep doctor --fix` handling the supported managed-runtime auto-repair path.
- Ensure post-upgrade verification is simple and user-visible.
- Define how breaking changes and deprecations are communicated.

### D. Managed Agent Runtime Compatibility

**Objective:** Make the autonomous-agent runtime version-aware instead of implicitly recreated when things drift.

- Add a version marker, catalog hash, or compatibility stamp to `~/.beepai/agents_env`.
- Define when the CLI should warn that the managed runtime is stale.
- Define when `beep agent setup` upgrades in place versus preserving the current runtime.
- Define when `beep agent reinstall` is required as an explicit repair operation.
- Surface runtime compatibility state in agent diagnostics/status output.

### E. Migration And Repair Policy

**Objective:** Make config, cache, and environment transitions safe across releases.

- Define migration rules for user config schema changes.
- Define migration or invalidation rules for sessions, caches, and other local state when formats change.
- Define what happens when managed-runtime package resolution fails mid-upgrade.
- Define repair and rollback expectations for partial installation failures.

### F. Release Validation And Publishing Gates

**Objective:** Enforce packaging quality in automation instead of relying on manual release memory.

- Turn the legacy release checklist into active CI/publishing gates.
- Validate build success for wheel and sdist artifacts.
- Add install-from-wheel smoke tests in a fresh environment.
- Add `pipx` smoke coverage against built artifacts.
- Add upgrade-path smoke coverage where a previous install is updated to a new artifact.
- Keep README install claims aligned with validated artifact flows.

## Todo Tracker

### A. Install Channels

- [x] Define the canonical end-user install path for Beep.AI.Code.
- [x] Document the support level for editable, wheel/sdist, `pipx`, and Git-based installs.
- [x] Document supported Python versions and environment assumptions.

### B. Distribution Strategy

- [x] Decide when PyPI publishing becomes required instead of optional.
- [x] Decide whether additional channels such as Homebrew, winget, or standalone binaries are in-scope for this roadmap.
- [x] Define release artifact expectations for wheel, sdist, and checksums or equivalent integrity metadata.

Policy decisions:
- **PyPI publishing** is deferred until the product reaches a stable 1.0 release. The primary
  distribution channel remains `pipx` from wheel/sdist artifacts until then. PyPI publishing
  should be enabled once the release checklist (`tools/ci/check_release_readiness.py`) passes
  at 100% for three consecutive releases without hotfixes.
- **Additional channels** (Homebrew, winget, Scoop, standalone binaries) are declared out of
  scope for this roadmap. The Python-first distribution via `pipx` and wheel install covers
  all target platforms (macOS, Linux, Windows) with a single artifact. OS-native channels may
  be revisited after 1.0 as a separate Phase 15 effort.
- **Release artifacts**: wheel and sdist are the minimum required outputs. A SHA256 checksum
  manifest (`SHA256SUMS.txt`) is generated for every release via
  `tools/ci/generate_release_checksums.py`. All artifacts are validated with `twine check`
  before acceptance. The release readiness checker (`tools/ci/check_release_readiness.py`)
  verifies 76 structural claims across core modules, agent runtime, chat, sessions, plugins,
  MCP, workspace, security, TUI, and CLI commands.

### C. Upgrade UX

- [x] Add explicit upgrade guidance and verification steps for the main CLI package.
- [x] Decide whether to add a dedicated CLI helper for upgrade or repair discovery.
- [x] Document deprecation and breaking-change communication rules.

### D. Managed Runtime Compatibility

- [x] Add a compatibility marker or version stamp for `~/.beepai/agents_env`.
- [x] Define stale-runtime detection in `beep agent status` or equivalent diagnostics.
- [x] Define when `beep agent setup` upgrades versus preserves an existing runtime.
- [x] Define when `beep agent reinstall` is the required recovery path.

### E. Migration And Repair

- [x] Define config migration policy across CLI releases.
- [x] Define cache/session invalidation or migration rules when formats change.
- [x] Define repair behavior for interrupted or partial runtime installation.

### F. CI And Release Gates

- [x] Add build validation for wheel and sdist artifacts.
- [x] Add install-from-artifact smoke tests in CI.
- [x] Add `pipx` smoke tests against built artifacts.
- [x] Add upgrade-path smoke tests from an older artifact to the current one.
- [x] Promote the legacy release checklist into the active release automation or release documentation.

## Acceptance Criteria

1. The repo defines a canonical install recommendation for contributors and end users instead of treating all install paths as equally supported.
2. Upgrading the main `beep` CLI package is documented with concrete commands and verification guidance.
3. The managed `~/.beepai/agents_env` runtime exposes a detectable compatibility state relative to the installed CLI.
4. Config and local-state migration rules are documented and testable.
5. Release automation validates wheel/sdist build integrity, install-from-artifact smoke paths, and `pipx` or equivalent end-user install flows.
6. The active packaging roadmap in `.plans/` is the canonical source of truth for release and upgrade lifecycle work.

## Out Of Scope For This Phase

- Replacing the package manager ecosystem with a non-Python-first distribution model.
- Shipping every possible OS-native installer in one pass.
- Rewriting the managed agent runtime into the main CLI environment.
- Changing Beep.AI.Server distribution strategy unless a shared contract requires it.