# Coding-Agent Parity (Claude Code / OpenCode)

**Status:** In Progress (Slices 1, 2, 5, 6 complete: Plan/Build toggle, @mention subagents, generic LSP, LiteLLM provider)  
**ID prefix:** `CAP`  
**Implementation plan:** [.plans/PHASE_21_CODING_AGENT_PARITY_V2.md](../../.plans/PHASE_21_CODING_AGENT_PARITY_V2.md) (7 slices, target files, tests, acceptance criteria)

Beep.AI.Code is positioned as a terminal coding agent in the same class as **Claude Code** and **OpenCode** (SST/Anomaly). This plan tracks the **capability gaps** to close for parity. Items cross-reference existing backlogs where they extend shipped work.

## Reference feature sets

| Capability | Claude Code | OpenCode | Beep.AI.Code today | Gap |
|------------|-------------|----------|--------------------|-----|
| Plan/Build mode toggle | ✓ | ✓ (Tab: build/plan) | Sandbox modes + `--mode`; no one-key toggle | Partial |
| Subagents | ✓ (Agent Teams) | ✓ (general/explore/scout, `@mention`) | `subagents/` (explore, plan, dispatch) | Partial (no `@mention`) |
| Persistent client/server sessions | resume from file | ✓ (server + SQLite, survives SSH drop) | Local JSONL sessions; no daemon | Missing |
| Parallel multi-session agents | Agent Teams | ✓ (up to 8, git worktrees) | Single `AgentSession` | Missing |
| Session share links | — | ✓ | — | Missing |
| LSP intelligence to LLM | ✓ | ✓ (auto-loads LSPs) | Jedi + tree-sitter (Python/TS); no generic LSP | Partial |
| IDE extensions / ACP | ✓ | ✓ (VS Code, Cursor, Zed, ACP) | — | Missing |
| Provider breadth + local | Anthropic | ✓ (75+, Ollama, models.dev) | OpenAI/Anthropic/OpenRouter/Beep packs | Partial |
| Hooks / automation | ✓ (29-hook system) | permissions rules | `hooks.json` (event hooks) | Partial |
| Skills marketplace | ✓ | skill packs | Local skills loader only | Partial (see INT) |
| MCP support | ✓ | ✓ | ✓ (presets, verify-tools) | Parity |
| Project memory | CLAUDE.md | AGENTS.md | `.beep.md` + AGENTS.md rules | Parity |

## Enhancement backlog

| ID | Item | Priority | Depends / ties | Verification |
|----|------|----------|----------------|----------------|
| CAP-1 | **Plan/Build toggle**: one-key switch (REPL hotkey + TUI Tab) mapping to read-only vs workspace-write sandbox, with a visible mode banner | P0 | `permissions/manager.py`, `chat/repl.py`, `tui/` | REPL/TUI mode-switch tests |
| CAP-2 | **`@mention` subagents** in chat (`@explore`, `@plan`, `@general`) routing to `agent/subagents/*` | P0 | `subagents/dispatcher.py`, `chat/commands/` | Dispatch test per mention |
| CAP-3 | **Persistent agent server/daemon**: background process holding session state so runs survive terminal/SSH exit; reconnect to in-flight run | P1 | NF-6 `beep serve`, sessions store | Reconnect integration test |
| CAP-4 | **Parallel multi-agent runs** each in an isolated git worktree, with a coordinator and result merge | P1 | AG-1, AG-2; `git_tool.py` | Worktree isolation test |
| CAP-5 | **Session share/export link** (HTML or server-hosted) for review/debug | P2 | NF-11, sessions exporter | Share artifact test |
| CAP-6 | **Generic LSP client** feeding diagnostics/hover/symbols to the model for any language | P1 | CX-3 | LSP smoke vs sample server |
| CAP-7 | **Editor integration via Agent Client Protocol (ACP)** + thin VS Code/Cursor/Zed adapters | P2 | NF-6, NF-7 | Protocol conformance test |
| CAP-8 | **Provider breadth + local models**: Ollama / LiteLLM / models.dev-style catalog; switch model per task | P1 | INT-4, `provider_*` | Provider matrix test |
| CAP-9 | **Hooks parity**: expand lifecycle events (pre/post tool, pre/post run, on-error, on-edit) and document the set | P2 | `hooks/manager.py` | Hook event-fire tests |
| CAP-10 | **Skills catalog/marketplace** with one-command install | P0 | INT-1 (integrations) | See INT plan |
| CAP-11 | **`/undo` + checkpoint timeline** for agent edits (revert to any step) | P2 | `editing/rollback.py`, graph checkpoints | Restore test |
| CAP-12 | **Cost/limit guardrails** surfaced like competitors (per-run budget, model price hints) | P1 | AG-4, NF-8 | Budget stop test |

## Recommended order

`CAP-1` and `CAP-2` first (cheap, high visibility, reuse shipped sandbox + subagents), then `CAP-10`/INT-1 (skills catalog — the headline ask), then `CAP-3`/`CAP-4` (persistence + parallelism), then `CAP-6`/`CAP-8` (LSP + providers).

Return to [../ENHANCEMENT_PLAN.md](../ENHANCEMENT_PLAN.md) · [integrations-catalog.md](integrations-catalog.md)
