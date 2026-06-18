# Built-in Integrations Catalog (Skills, Tools & MCP)

**Status:** In Progress (Slices 1-6 implemented)  
**ID prefix:** `INT`  
**Implementation plan:** [.plans/PHASE_20_INTEGRATIONS_CATALOG.md](../../.plans/PHASE_20_INTEGRATIONS_CATALOG.md) (7 slices, target files, tests, acceptance criteria)

Make Beep.AI.Code ship with a **curated, one-command catalog** of well-known packages and tools that coders and agents rely on — the way Claude Code / OpenCode expose skills, MCP servers, and tool integrations. Users should be able to discover and enable a capability without hand-editing config.

## What "integration" means here

Beep already has the runtime primitives:

| Primitive | Today | This plan adds |
|-----------|-------|----------------|
| Skills (`beep/skills/`) | Local markdown packs only | A **named registry** + `beep skills add <name>` install |
| MCP (`beep/mcp/presets.py`) | Built-in presets + verify-tools | A **larger curated preset catalog** of top servers |
| External CLI tools | Used ad hoc by agent shell tool | A **detector/installer** (`beep tools`) that reports availability |
| Providers (`beep/agent/provider_*`) | OpenAI/Anthropic/OpenRouter/Beep | **Local + gateway** providers (Ollama, LiteLLM) |

## Seed catalog (examples requested + common picks)

> Security note: third-party skills/tools execute code or reach the network. Every catalog entry must carry a **source URL, pinned version/commit, and trust tier**, and install must be **explicit and gated** (no silent auto-fetch). Community entries are vetted before bundling; until vetted they are listed as `external` and installed only on explicit user confirmation.

### Agent skills

| Skill | Source | Purpose | Trust tier |
|-------|--------|---------|-----------|
| `open-design` | [nexu-io/open-design](https://github.com/nexu-io/open-design) | Design systems, UI/prototype/slide/image generation | external (vet) |
| `graphify` | [safishamsi/graphify](https://github.com/safishamsi/graphify) | Turn a repo (code, SQL, docs) into a queryable knowledge graph | external (vet) |
| `code-review` | built-in | Standards-aware review preset | first-party |
| `test-author` | built-in | Test generation preset | first-party |

### MCP servers (expand `presets.py`)

| Server | Purpose |
|--------|---------|
| GitHub MCP | Issues, PRs, repo ops |
| Playwright / Puppeteer MCP | Browser automation, e2e |
| Filesystem MCP | Sandboxed file ops |
| Fetch / web MCP | URL fetch |
| Context7 | Up-to-date library docs |
| Tavily / Brave Search | Web search (also see NF-1) |
| Postgres / SQLite MCP | DB introspection + queries |
| Sentry MCP | Error context |
| Semble | Semantic code search (already integrated) |

### External developer tools (`beep tools`)

`ripgrep (rg)`, `fd`, `gh` (GitHub CLI), `semgrep`, `ruff`, `mypy`, `eslint`, `prettier`, `jq`, `docker`, `node`, `git` — detect presence, surface to the agent tool layer, and offer install hints per OS.

### Providers / local models

`Ollama`, `llama.cpp`, `LiteLLM` gateway, plus a **validated model catalog** (models.dev-style) for "known-good coding models".

## Enhancement backlog

| ID | Item | Priority | Notes / ties | Verification |
|----|------|----------|--------------|----------------|
| INT-1 | **Skills registry + install** (`beep skills list/add/remove/update/info`), reading a curated index file; per-entry source, version pin, trust tier; gated network fetch | P0 | `beep/skills/`, CAP-10 | Install/uninstall tests; offline-default test |
| INT-2 | **Expand MCP preset catalog** with the servers above; each with verified `*_TOOLS` contracts and `beep mcp verify-tools` coverage | P0 | `beep/mcp/presets.py`, `preset_tools.py` | Contract tests per server |
| INT-3 | **External tool detector/installer** (`beep tools list/doctor`) feeding availability into agent tool factory and `beep diagnostics` | P1 | `agent/tools/factory.py`, diagnostics | Detector unit tests (mock PATH) |
| INT-8 | **Integration governance**: trust tiers, version pinning, checksum/signature verification, `--no-integrations` gate, audit log | P0 | security, permissions | Security policy tests |
| INT-9 | **Catalog UX**: `beep catalog` to browse/search skills+MCP+tools in one place (rows-default per UX rules) | P2 | new command | CLI/render test |

## Why this matters

Competitors win on **ecosystem reach** (skills marketplaces, broad MCP, local models). Beep already has the substrate (skills loader, MCP runtime, provider packs); INT turns that substrate into a **discoverable, governed, one-command catalog** without coupling to any single vendor — consistent with the repo's standards-first, code-first rules.

## Governance reminder (repo rules)

- Catalog entries that affect behavior are **code/typed config**, not bare JSON (`AGENTS.md` code-first rule); the JSON index only stores user-installed state.
- Network/shell-reaching integrations stay **off by default** and explicitly gated, mirroring the `BEEP_MCP` pattern.

Return to [../ENHANCEMENT_PLAN.md](../ENHANCEMENT_PLAN.md) · [coding-agent-parity.md](coding-agent-parity.md) · [mcp-bridge.md](mcp-bridge.md) · [memory-rules-skills.md](memory-rules-skills.md)
