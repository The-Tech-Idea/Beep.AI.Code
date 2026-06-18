# Beep.AI.Code — Documentation Index

**Repository:** [Beep.AI.Code](https://github.com/The-Tech-Idea/Beep.AI.Code)  
**Package:** `beep-ai-code` · **CLI:** `beep`  
**Server dependency:** [Beep.AI.Server](https://github.com/The-Tech-Idea/Beep.AI.Server)

---

## Start here

| Document | Audience | Summary |
|----------|----------|---------|
| [APP_OVERVIEW.md](APP_OVERVIEW.md) | Everyone | What the CLI is, how it connects to the server, runtime model |
| [CLI_AND_COMMANDS.md](CLI_AND_COMMANDS.md) | Users / operators | Command and REPL surface reference |
| [SERVICES_REGISTRY.md](SERVICES_REGISTRY.md) | Contributors | `AppService`, domains, and package map |
| [ENHANCEMENT_PLAN.md](ENHANCEMENT_PLAN.md) | PM / contributors | Master enhancement roadmap with per-feature plans |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Contributors | Runtime layers, ownership, clean-code boundaries |
| [../README.md](../README.md) | Users | Install, setup, daily usage, troubleshooting |
| [../MASTER-TODO-TRACKER.md](../MASTER-TODO-TRACKER.md) | Contributors | Canonical phased execution tracker (`.plans/` phases) |

---

## Feature enhancement plans

Each plan describes **current behavior**, **code locations**, and a **prioritized enhancement backlog**.

| Feature | Plan |
|---------|------|
| Beep.AI.Server integration (default backend) | [features/server-integration.md](features/server-integration.md) |
| Integrations catalog (skills/MCP/tools) | [features/integrations-catalog.md](features/integrations-catalog.md) |
| Coding-agent parity (Claude Code/OpenCode) | [features/coding-agent-parity.md](features/coding-agent-parity.md) |
| New features (greenfield) | [features/new-features.md](features/new-features.md) |
| API client & streaming | [features/api-client.md](features/api-client.md) |
| Coding Assistant bridge | [features/coding-assistant.md](features/coding-assistant.md) |
| Chat REPL & slash commands | [features/chat-repl.md](features/chat-repl.md) |
| Agent runtime (LangGraph) | [features/agent-runtime.md](features/agent-runtime.md) |
| Workspace & editing | [features/workspace-editing.md](features/workspace-editing.md) |
| Context & intelligence | [features/context-and-intelligence.md](features/context-and-intelligence.md) |
| Memory, rules, skills | [features/memory-rules-skills.md](features/memory-rules-skills.md) |
| Plugins | [features/plugins.md](features/plugins.md) |
| MCP bridge | [features/mcp-bridge.md](features/mcp-bridge.md) |
| Templates | [features/templates.md](features/templates.md) |
| Sessions & compaction | [features/sessions.md](features/sessions.md) |
| RAG | [features/rag.md](features/rag.md) |
| Code analysis & indexing | [features/code-analysis-indexing.md](features/code-analysis-indexing.md) |
| Quality commands (test/lint/review) | [features/quality-commands.md](features/quality-commands.md) |
| Permissions, sandbox, hooks | [features/permissions-sandbox-hooks.md](features/permissions-sandbox-hooks.md) |
| Watcher, tasks, bookmarks | [features/watcher-tasks-bookmarks.md](features/watcher-tasks-bookmarks.md) |
| TUI | [features/tui.md](features/tui.md) |
| Publishing & agent bundles | [features/publishing-and-bundles.md](features/publishing-and-bundles.md) |
| Diagnostics & updates | [features/diagnostics-packaging-updates.md](features/diagnostics-packaging-updates.md) |
| Configuration & setup | [features/configuration-setup.md](features/configuration-setup.md) |

Index of feature folders: [features/README.md](features/README.md).

---

## Engineering standards

| Document | Notes |
|----------|--------|
| [ENGINEERING_IMPLEMENTATION_GUIDELINES.md](ENGINEERING_IMPLEMENTATION_GUIDELINES.md) | Cross-cutting implementation rules (originated in Beep.AI.Server workspace; applies to CLI changes that touch APIs and auth) |
| [INSTALL_AND_UPDATE.md](INSTALL_AND_UPDATE.md) | Install channels and update workflows |
| [../AGENTS.md](../AGENTS.md) | Ecosystem agent-framework rules when integrating with the server |

---

## Historical / server monorepo notes

These files describe server extraction or debug routes from an earlier monorepo layout. Prefer the documents above for **Beep.AI.Code** work unless you are changing server integration contracts.

- [PHASE_3_QUICK_REFERENCE.md](PHASE_3_QUICK_REFERENCE.md)
- [PHASE_3_EXTRACTION_INTEGRATION.md](PHASE_3_EXTRACTION_INTEGRATION.md)
- [PHASE_3_7_DEBUG_ROUTES.md](PHASE_3_7_DEBUG_ROUTES.md)

---

*Last updated: documentation suite for Beep.AI.Code app scan.*
