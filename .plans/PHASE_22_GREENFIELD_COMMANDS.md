# Phase 22 — Greenfield Commands (Web Search, Git Family, `beep init`)

## Goal

Add three net-new, high-value command surfaces that bring Beep.AI.Code to parity with everyday coding-agent workflows:

1. **Web search** — fill the empty `beep/websearch/` package with a real, gated search capability for chat and the agent.
2. **First-class git family** — promote the existing chat git workflow (`/commit`, `/branch`, `/pr`, `/diff`) to top-level `beep` commands via a shared service.
3. **`beep init`** — guided onboarding that scaffolds project memory, rules, skills, and ignore files.

Backing feature doc: [docs/features/new-features.md](../docs/features/new-features.md) (NF-1, NF-2, NF-3).

## Existing substrate (verified)

- `beep/websearch/__init__.py` — **empty stub** (greenfield).
- `beep/chat/commands/workflow.py` — `BashCommand`, `DiffCommand`, `CommitCommand`, `BranchCommand`, `PRCommand`, `RevertCommand`, `OutputCommand` (chat slash commands already implemented).
- `beep/workspace/git.py` — `get_git_status/diff/diff_for_file/log`, `is_git_repo` helpers.
- `beep/agent/tools/git_tool.py` — agent-side allowlisted git tool.
- `beep/memory/loader.py`, `beep/rules/loader.py`, `beep/skills/loader.py` — discovery roots for `.beep.md`, rules, skills.
- `beep/setup_wizard.py` — existing wizard patterns to mirror.
- `beep/cli_command_registration.py` — central command registration.

## Guiding principles

- One file = one concern; ≤500 lines (split near 300).
- **No duplication:** extract a shared **git workflow service** so chat slash commands and the new CLI commands call the same logic (clean-code rule; mirrors `workspace/search.py`, `workspace/view.py`, `workspace/editing.py` convergence).
- Network/shell-reaching features are **off by default** and explicitly gated.
- Isolated test file per module.

---

## Slice 1 — Web search (NF-1)

### ws-1.1 Provider abstraction
- [ ] Create `beep/websearch/models.py`: `SearchQuery`, `SearchResult(title, url, snippet)`, `SearchProvider` protocol
- [ ] Create `beep/websearch/providers.py`: pluggable providers (e.g. Tavily, Brave, SearXNG) selected by config key; HTTP via existing client patterns
- [ ] Create `beep/websearch/service.py`: `WebSearchService.search(query) -> list[SearchResult]`, with result cap + timeout
- [ ] `tests/test_websearch_service.py` — mocked provider; no real network in tests

### ws-1.2 Config + gate
- [ ] Extend `beep/config.py`: `websearch_provider`, provider API key field(s)
- [ ] Gate: require `BEEP_WEBSEARCH=1` (truthy variants) or explicit `--allow-network`, mirroring `BEEP_MCP`
- [ ] `tests/test_websearch_config.py` — gate matrix

### ws-1.3 AppService singleton
- [ ] Add `web_search` (keyed by provider+config) to `beep/app_service.py`; add to `reset()`; update [docs/SERVICES_REGISTRY.md](../docs/SERVICES_REGISTRY.md) and AGENTS.md list

### ws-1.4 Agent tool + chat slash + CLI
- [ ] Create `beep/agent/tools/web_search.py`: `WebSearchTool(BaseTool)` (read-only, gated); register in `agent/tools/factory.py`
- [ ] Add `/search <query>` chat command (`beep/chat/commands/`)
- [ ] Add `beep search <query>` CLI command (`beep/commands/search.py`); register in `cli_command_registration.py`
- [ ] Tests: tool contract, slash dispatch, CLI smoke

**Verification:** with gate on + mocked provider, `beep search "..."`, `/search`, and the agent tool return formatted results with citations; gate-off path is denied with a friendly message.

---

## Slice 2 — First-class git family (NF-2)

Promote chat git behavior to top-level CLI by extracting a shared service.

### git-2.1 Shared workflow service
- [ ] Create `beep/vcs/workflow.py`: `GitWorkflow` with `status()`, `diff(staged, file)`, `commit(message, *, ai_message, all)`, `branch(name, base)`, `pull_request(title, body, base, draft)` — wraps `beep/workspace/git.py` and shells `git`/`gh` where needed
- [ ] Move AI commit-message / PR-body generation into the service so it is reusable (callable with a client/model)
- [ ] `tests/test_vcs_workflow.py` — temp repo; status/diff/commit; `gh` calls mocked

### git-2.2 Refactor chat commands onto the service
- [ ] Update `beep/chat/commands/workflow.py`: `CommitCommand`, `BranchCommand`, `PRCommand`, `DiffCommand` delegate to `GitWorkflow` (no behavior change)
- [ ] Regression: existing chat command tests still pass

### git-2.3 CLI commands
- [ ] Create `beep/commands/git.py`: `commit_cmd`, `branch_cmd`, `pr_cmd`, `diff_cmd` (and `status`), reusing `GitWorkflow`
  - `beep commit` (`-m`, `--ai` for generated message, `--all`)
  - `beep branch <name>` (`--base`)
  - `beep pr` (`--title`, `--body`, `--ai`, `--draft`, `--base`)
  - `beep diff` (`--staged`, `--file`)
- [ ] Register a `git` group **or** top-level `commit`/`pr`/`branch`/`diff` in `cli_command_registration.py` (decide one; document)
- [ ] Graceful errors when not a repo / `gh` missing (tie INT-3 tool detector)
- [ ] `tests/test_git_commands.py` — temp repo CLI tests

**Verification:** `beep commit --ai`, `beep pr --ai --draft`, `beep diff --staged`, `beep branch feat/x` work in a temp repo; chat `/commit` etc. unchanged and now share the service.

---

## Slice 3 — `beep init` onboarding (NF-3)

### init-3.1 Scaffold service
- [ ] Create `beep/onboarding/scaffold.py`: `ScaffoldPlan` describing files to write — `.beep.md`, `.beep/rules.md` (or `AGENTS.md`), `.beep/skills/` sample, `.beep/ignore`, optional `.beep/commands.md`
- [ ] Templates are **typed Python** (code-first rule); only generated user files are written to disk
- [ ] Idempotent: never overwrite without `--force`; report created vs skipped
- [ ] `tests/test_onboarding_scaffold.py` — temp workspace; created/skipped/force

### init-3.2 Interactive wizard
- [ ] Create `beep/commands/init.py`: `init_cmd` — detect workspace root (`workspace/detector.py`), prompt for project description / language / conventions, write scaffold; `--yes` non-interactive defaults
- [ ] Mirror `setup_wizard.py` UX; simple default + advanced toggle per repo UX rules
- [ ] Register `init` in `cli_command_registration.py`
- [ ] `tests/test_init_command.py` — non-interactive run on temp workspace

### init-3.3 Discovery confirmation
- [ ] After scaffold, run the existing loaders (`memory/rules/skills`) and report what the agent will now load
- [ ] Test: loaders pick up scaffolded files

**Verification:** `beep init --yes` in an empty dir creates `.beep.md` + `.beep/` tree; rerun reports skips; loaders confirm pickup.

---

## Slice 4 — Docs + tracker sync

- [ ] Update [docs/CLI_AND_COMMANDS.md](../docs/CLI_AND_COMMANDS.md): add `search`, git family, `init`
- [ ] Update [README.md](../README.md) features-at-a-glance + daily-usage
- [ ] Update [docs/features/new-features.md](../docs/features/new-features.md): mark NF-1/NF-2/NF-3 as in-progress/shipped per slice
- [ ] Flip `PH-22` status in [MASTER-TODO-TRACKER.md](../MASTER-TODO-TRACKER.md)

---

## Acceptance criteria

- [ ] Web search works for chat, agent tool, and `beep search`, **off by default** and gated; results carry citations.
- [ ] `beep commit/branch/pr/diff` work and **share one service** with the chat slash commands (no duplicated logic).
- [ ] `beep init` scaffolds project memory/rules/skills idempotently and the loaders pick them up.
- [ ] All new modules ≤500 lines, one concern each, with isolated tests.
- [ ] `pytest -q`, `ruff check beep tests`, `mypy beep` green (Windows tmp-path caveat tracked in X-1).

## Sequencing

`Slice 2 (git family)` is the lowest-risk (promotes proven chat logic) and a good warm-up; `Slice 3 (init)` activates already-built memory/rules/skills; `Slice 1 (web search)` is the only true greenfield with network concerns — gate it carefully. Recommended order: **2 → 3 → 1**.

## Out of scope (follow-on NF items)

- `beep explain` (NF-4), `beep docs generate` (NF-5), `beep serve`/`lsp` (NF-6/7 → PH-21), usage analytics (NF-8), scheduled runs (NF-9), multi-repo switcher (NF-10), HTML export (NF-11), notebooks (NF-12), image output (NF-13), snippets (NF-14), branching (NF-15).
