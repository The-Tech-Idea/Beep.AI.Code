# Phase 20 — Built-in Integrations Catalog (Skills + MCP + Tools)

## Goal

Ship a **curated, governed, one-command catalog** so coders and agents can discover and enable well-known skills, MCP servers, and developer tools without hand-editing config. This is the top initiative from [docs/features/integrations-catalog.md](../docs/features/integrations-catalog.md).

Reference companions: [docs/features/coding-agent-parity.md](../docs/features/coding-agent-parity.md) (PH-21), [docs/ENHANCEMENT_PLAN.md](../docs/ENHANCEMENT_PLAN.md).

## Scope (this phase)

- Skills **registry + install/list/remove/update** (INT-1)
- **Governance** layer: trust tiers, version pins, integrity check, off-by-default network gate, audit log (INT-8)
- **Expanded MCP preset catalog** with verified contracts (INT-2)
- **External tool detector** feeding agent + diagnostics (INT-3)
- `beep catalog` browse command (INT-9)

Deferred to follow-on phases: local providers/Ollama (INT-4 → PH-21 CAP-8), graphify/open-design deep wiring (INT-5/6), validated model catalog (INT-7).

## Guiding principles (repo rules)

- One file = one business concern; hard limit 500 lines, split near 300.
- **Code-first:** the catalog index and entry definitions are **typed Python** validated at import time. JSON stores only **user-installed state** (`~/.beepai/integrations/installed.json`), never behavior.
- All new long-lived services registered on `AppService`.
- Network/shell-reaching integrations are **off by default** and explicitly gated, mirroring `BEEP_MCP`.
- Each module ships with an isolated test file.

## Architecture

```text
beep/integrations/
├── __init__.py
├── models.py              # CatalogEntry, TrustTier, InstalledRecord (pydantic, typed)
├── catalog.py             # CURATED_ENTRIES (code-first registry), lookup/search
├── governance.py          # trust-tier policy, version pin, checksum/signature verify, gate
├── installer.py           # install/remove/update; writes installed.json atomically
├── audit.py               # append-only audit log of install/enable/disable
├── skills_source.py       # fetch+materialize a skill entry into ~/.beepai/skills/<name>/
└── tool_detector.py       # detect external CLI tools on PATH (rg, gh, semgrep, …)

beep/commands/
├── skills.py              # beep skills list|add|remove|update|info
└── catalog.py             # beep catalog (browse skills+mcp+tools, rows-default)

beep/mcp/presets.py        # EXTEND: add curated servers
beep/mcp/preset_tools.py   # EXTEND: verified *_TOOLS contracts per new server
beep/app_service.py        # register integrations registry singleton
beep/cli_command_registration.py  # register skills + catalog commands
```

State file: `~/.beepai/integrations/installed.json` (mode 0600, atomic write).

---

## Slice 1 — Catalog models + curated index (code-first)

### int-1.1 Models
- [ ] Create `beep/integrations/__init__.py`
- [ ] Create `beep/integrations/models.py`:
  - `TrustTier(StrEnum)`: `first_party`, `verified`, `external`
  - `EntryKind(StrEnum)`: `skill`, `mcp`, `tool`
  - `CatalogEntry`: `id`, `kind`, `name`, `summary`, `source_url`, `version` (pin/commit), `trust`, `requires_network: bool`, `install_hint`, `tags: list[str]`
  - `InstalledRecord`: `id`, `version`, `installed_at`, `source_url`, `checksum`
- [ ] `tests/test_integrations_models.py` — validation, enum coercion

### int-1.2 Curated catalog
- [ ] Create `beep/integrations/catalog.py` with `CURATED_ENTRIES: tuple[CatalogEntry, ...]` seeded:
  - skills: `open-design` (external), `graphify` (external), `code-review` (first_party), `test-author` (first_party)
  - mcp refs: pointers to `presets.py` ids (github, playwright, context7, tavily, postgres, sentry, filesystem, fetch)
  - tools: `ripgrep`, `fd`, `gh`, `semgrep`, `ruff`, `mypy`, `eslint`, `prettier`, `jq`, `docker`, `node`, `git`
  - `find(entry_id)`, `search(query, kind=None)` helpers
- [ ] Import-time validation: unique ids, external entries must set `requires_network`
- [ ] `tests/test_integrations_catalog.py` — lookup, search, validation guard

**Verification:** `python -c "from beep.integrations.catalog import CURATED_ENTRIES"` imports clean; tests pass.

---

## Slice 2 — Governance + audit

### int-2.1 Governance policy
- [ ] Create `beep/integrations/governance.py`:
  - `is_install_allowed(entry, *, allow_external: bool, network_enabled: bool) -> Decision`
  - external tier requires explicit `--yes`/confirm; network entries require gate (`BEEP_INTEGRATIONS=1` or `--allow-network`)
  - `verify_integrity(path, expected_checksum) -> bool`
- [ ] `tests/test_integrations_governance.py` — gate matrix (first_party/verified/external × network on/off)

### int-2.2 Audit log
- [ ] Create `beep/integrations/audit.py` — append-only JSONL at `~/.beepai/integrations/audit.log`; `record(action, entry_id, outcome)`
- [ ] `tests/test_integrations_audit.py` — append + read-back

**Verification:** external + network-off is denied without confirm; audit entries written for every action.

---

## Slice 3 — Installer + skills source

### int-3.1 Installer
- [ ] Create `beep/integrations/installer.py`:
  - `install(entry, *, allow_external, network_enabled) -> InstalledRecord`
  - `remove(entry_id)`, `update(entry_id)`, `list_installed() -> list[InstalledRecord]`
  - atomic write of `installed.json` (reuse `sessions/history_support.py` atomic pattern)
- [ ] `tests/test_integrations_installer.py` — install→list→remove round-trip with a fake skill source

### int-3.2 Skill materialization
- [ ] Create `beep/integrations/skills_source.py`:
  - For `kind=skill`: fetch pinned source (git archive or release zip) into `~/.beepai/skills/<id>/` so the existing `beep/skills/loader.py` discovers it with no loader change
  - checksum the materialized tree; pass to governance
- [ ] `tests/test_skills_source.py` — materialize from a local fixture path (no real network in tests)

**Verification:** after `install("graphify")` (fixture), `load_skills()` returns the new skill; `remove` cleans the directory.

---

## Slice 4 — External tool detector

### int-4.1 Detector
- [ ] Create `beep/integrations/tool_detector.py`:
  - `detect(tool_id) -> ToolStatus(found, path, version, install_hint)`
  - `detect_all() -> list[ToolStatus]` for catalog tool entries (uses `shutil.which`, light `--version`)
- [ ] `tests/test_tool_detector.py` — monkeypatch PATH; found/not-found

### int-4.2 Wire into diagnostics + agent
- [ ] Update `beep/commands/diagnostics.py` (or schema support) to include tool availability section
- [ ] Update `beep/agent/tools/factory.py` to expose detected tools to the agent (capability hints only; no auto-exec)
- [ ] Tests: diagnostics output includes tools; factory hint test

**Verification:** `beep diagnostics` lists tool availability; missing tools show install hints.

---

## Slice 5 — AppService + CLI surface

### int-5.1 AppService singleton
- [ ] Add `integrations` property to `beep/app_service.py` returning an `IntegrationsRegistry` (wraps catalog + installer + audit); add to `reset()`
- [ ] Update [AGENTS.md](../AGENTS.md) AppService list + [docs/SERVICES_REGISTRY.md](../docs/SERVICES_REGISTRY.md)
- [ ] `tests/test_app_service.py` — singleton identity for `integrations`

### int-5.2 `beep skills` command group
- [ ] Create `beep/commands/skills.py`: `list`, `add <id> [--yes] [--allow-network]`, `remove <id>`, `update <id>`, `info <id>`
- [ ] Rows-default output per UX rules; friendly errors; honor `--no-integrations` global gate
- [ ] `tests/test_skills_command.py`

### int-5.3 `beep catalog` command
- [ ] Create `beep/commands/catalog.py`: browse/search all kinds (skills+mcp+tools), rows-default with optional `--kind`
- [ ] `tests/test_catalog_command.py`

### int-5.4 Register commands
- [ ] Update `beep/cli_command_registration.py`:
  - add `skills` group (`list/add/remove/update/info`)
  - add `catalog` top-level command
- [ ] `tests/test_cli_smoke.py` — help lists new commands; default-dispatch unaffected

**Verification:** `beep skills list`, `beep skills add code-review`, `beep catalog --kind mcp`, `beep --help` all work.

---

## Slice 6 — Expanded MCP preset catalog

### int-6.1 Add presets
- [ ] Extend `beep/mcp/presets.py` with: github, playwright, context7, tavily (search), postgres, sentry, filesystem, fetch (launch metadata only; off by default)
- [ ] Extend `beep/mcp/preset_tools.py` with verified `*_TOOLS` contracts (doc-backed); leave launch-only where tools unverified
- [ ] `tests/test_mcp_presets.py` / `test_mcp_preset_tools.py` — preset loads, contract shape, `verify-tools` path

**Verification:** `beep mcp presets` lists new servers; `beep mcp verify-tools <server> --from-file fixture.json` validates contracts.

---

## Slice 7 — Docs + tracker sync

- [ ] Update [docs/features/integrations-catalog.md](../docs/features/integrations-catalog.md): mark INT-1/2/3/8/9 shipped as slices land
- [ ] Update [docs/CLI_AND_COMMANDS.md](../docs/CLI_AND_COMMANDS.md): add `skills`, `catalog` groups
- [ ] Update [README.md](../README.md) features-at-a-glance with integrations catalog
- [ ] Flip `PH-20` status in [MASTER-TODO-TRACKER.md](../MASTER-TODO-TRACKER.md) to `[~]`/`[x]` as appropriate

---

## Acceptance criteria

- [ ] `beep skills list/add/remove/update/info` and `beep catalog` work end-to-end with the seed catalog.
- [ ] External/network entries are **denied by default** and require explicit confirm + gate; every action audited.
- [ ] Installing a skill makes it visible to the existing skills loader with **no loader change**.
- [ ] Expanded MCP presets pass contract/verify tests.
- [ ] `beep diagnostics` reports external tool availability.
- [ ] All new modules ≤ 500 lines, one concern each, with isolated tests.
- [ ] `pytest -q`, `ruff check beep tests`, `mypy beep` green (Windows tmp-path caveat tracked in X-1).

## Out of scope (follow-on)

- Local providers / Ollama / LiteLLM (PH-21 CAP-8, INT-4)
- Deep graphify→context/RAG and open-design→agent wiring (INT-5, INT-6)
- Validated model catalog (INT-7)
- Signature/keyring-based publisher trust (extends INT-8)

## Security note

`open-design` and `graphify` are seeded at `external` trust tier. They are **not bundled**; they install only on explicit confirmation with a pinned source and integrity check. Review upstream contents before promoting either to `verified`.
