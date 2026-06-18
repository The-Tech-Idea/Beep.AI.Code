# New Features (Greenfield)

**Status:** In Progress (NF-1: web search shipped with BEEP_WEBSEARCH=1 gate; NF-2: git family shipped via GitWorkflow service; NF-3: beep init shipped with scaffold)  
**Implementation plan (NF-1/2/3):** [.plans/PHASE_22_GREENFIELD_COMMANDS.md](../../.plans/PHASE_22_GREENFIELD_COMMANDS.md) (4 slices, target files, tests, acceptance criteria)  
**Scope:** Capabilities the CLI does **not** have today — distinct from the incremental enhancement backlogs in the other `docs/features/*` files.

Each item lists rationale, the new user surface, key dependencies, and a verification gate. ID prefix: **`NF`**.

## Grounding (verified by scan)

| Observation | Implication |
|-------------|-------------|
| `beep/websearch/__init__.py` is an empty stub | Web search is genuinely new, not an enhancement |
| `beep/agent/tools/git_tool.py` exists; chat has `/commit`, `/pr` | Agent can touch git, but there is **no top-level `beep` git command family** |
| Multimodal input flags exist on `beep agent` (`--input-image`) | Image-in is partial; image/diagram **output** and screenshot capture are new |
| No `serve` / `init` / `explain` / `docs` commands in `beep/commands/` | These are new entry points |

---

## Tier 1 — high value, well-scoped

| ID | Feature | Why | New surface | Depends on | Verification |
|----|---------|-----|-------------|------------|----------------|
| NF-1 | **Web search tool** | `websearch` is an empty package; agents need current info | Agent tool `web_search`; `/search` slash; optional `beep search` | HTTP client, provider key/config, gate like MCP | Tool contract test + mocked provider |
| NF-2 | **Git command family** (`beep commit`, `beep pr`, `beep branch`) | AI commit messages / PR bodies exist only inside chat; promote to first-class CLI | New `beep/commands/git.py` reusing `agent/tools/git_tool.py` | `git`, optional `gh` | CLI tests with temp repo |
| NF-3 | **`beep init`** project onboarding | New users have no guided way to scaffold `.beep.md`, rules, skills, ignore | Interactive wizard writing workspace memory/rules/skills templates | memory/rules/skills loaders | Wizard test on temp workspace |
| NF-4 | **`beep explain <path|symbol>`** | One-shot, focused explanation without entering chat | New command + context builder reuse | smart context, code index | CLI snapshot test |
| NF-5 | **`beep docs generate`** | Generate/update docstrings or README sections from code | New command, agent task preset | agent runtime, templates | Generated-output test |

## Tier 2 — platform / integration

| ID | Feature | Why | New surface | Depends on | Verification |
|----|---------|-----|-------------|------------|----------------|
| NF-6 | **`beep serve` local API** | Let editors/scripts drive the local agent over HTTP (IDE/SDK integration) | Local FastAPI/uvicorn exposing chat + agent | agent runtime, auth token | Endpoint integration test |
| NF-7 | **LSP / editor bridge** | Surface beep actions inside editors via Language Server Protocol | New `beep lsp` server | NF-6 or direct | Protocol smoke test |
| NF-8 | **Cost & usage analytics** | No spend/usage visibility today | `beep usage` + per-session token/cost rollup | session store, server usage payloads | Aggregation unit test |
| NF-9 | **Scheduled / unattended agent runs** | Cron-style "run this goal nightly", CI bots | `beep agent schedule` + run record | agent runtime, bundles | Dry-run schedule test |
| NF-10 | **Multi-repo / workspace switcher** | Operators juggle several repos; config is single-workspace | `beep workspace use <path>`, profiles | config profiles (CF-3) | Multi-root test |

## Tier 3 — experience / reach

| ID | Feature | Why | New surface | Depends on | Verification |
|----|---------|-----|-------------|------------|----------------|
| NF-11 | **Shareable session export to HTML** | Sessions export to md/json only; HTML is portable for review | `beep sessions export --format html` | sessions exporter | Render test |
| NF-12 | **Jupyter notebook (`.ipynb`) support** | Cat/edit/agent break on notebooks | Notebook-aware view/edit adapter | workspace view/editing | Notebook fixture test |
| NF-13 | **Screenshot / diagram capture in agent output** | Agents can take image input but not emit visuals | Image artifact emit + render path | multimodal, TUI/terminal image | Artifact path test |
| NF-14 | **Snippets / prompt library** | No reusable prompt/snippet store | `beep snippet save/use`, `/snippet` | config dir store | CRUD test |
| NF-15 | **Conversation branching** | Linear sessions only; branching enables exploration | Fork session at message N | session store | Branch/restore test |

---

## Recommended first three

1. **NF-1 Web search tool** — fills an empty package and directly improves agent quality.
2. **NF-2 Git command family** — promotes already-proven chat behavior to first-class CLI with low risk.
3. **NF-3 `beep init`** — biggest onboarding lift for new users; activates memory/rules/skills that already exist.

Each should ship with: a feature flag or env gate where it reaches the network or shell, tests, and a docs update in this file plus the matching `docs/features/*` cross-link.

---

## Relationship to existing backlogs

These are **new capabilities**; the per-feature files cover **hardening existing ones**. Where a new feature builds on an existing area, the dependency is noted above (e.g. NF-10 depends on CF-3 config profiles, NF-13 depends on multimodal in the agent runtime).

Return to [../ENHANCEMENT_PLAN.md](../ENHANCEMENT_PLAN.md) · [README.md](README.md)
