# Services & Domain Registry

All long-lived managers should be accessed through **`get_app_service()`** ([`beep/app_service.py`](../beep/app_service.py)). Do not construct service classes ad hoc in commands.

```python
from beep.app_service import get_app_service

app = get_app_service()
app.code_analysis.analyze_project(path)
```

## AppService singletons

| Property / factory | Type (domain) | Scope | Primary use |
|--------------------|---------------|-------|-------------|
| `code_analysis` | `CodeAnalysisService` | Process | Project stats, architecture/semgrep analysis |
| `bookmarks` | `BookmarkManager` | Process | Saved file bookmarks |
| `tasks` | `TaskManager` | Process | REPL `/task` tracking |
| `permissions` | `PermissionManager` | Process | Tool approval policy |
| `hooks` | `HookConfig` | Process | `~/.beepai/hooks.json` |
| `language_registry` | `LanguageRegistry` | Process | Language adapters |
| `template_registry` | `ProjectTemplateRegistry` | Process | Scaffold plugins (Go, Rust, …) |
| `template_validator` | `ProjectTemplateValidator` | Process | Template validation |
| `rollback` | `RollbackManager` | Process | Edit undo stacks |
| `standards_reviewer` | `StandardsReviewer` | Process | Standards-oriented review helpers |
| `tree_sitter_parser` | `TreeSitterParser` | Process | Syntax-aware indexing |
| `watcher(root)` | `WatcherService` | Per workspace root | File watch callbacks |
| `api_client(config)` | `BeepAPIClient` | Per URL+token | Server HTTP |
| `mcp_client(servers)` | `MCPClient` | Per MCP config hash | MCP tool bridge |
| `smart_context(root)` | `SmartContextBuilder` | Per workspace | File selection for prompts |
| `auto_context(root)` | `AutoContextBuilder` | Per workspace | Auto context + Semble |
| `chat_context(root)` | `ChatContext` | Per workspace | Pinned files |
| `python_jedi(root)` | `PythonJediAdapter` | Per workspace | Python intelligence tools |
| `semble_index(root)` | `SembleIndexAdapter` | Per workspace | Semantic code search |
| `plugin_registry(root)` | `PluginRegistry` | Per workspace | Plugin load/dispatch |
| `session_manager(config, client)` | `SessionManager` | Per call | **Not** global; bound to chat session |

`AppService.reset()` / `reset_registry()` — test isolation.

## Package map (by domain)

| Domain | Path | Role |
|--------|------|------|
| API | `beep/api/` | Client, payloads, streaming, agent bundle HTTP |
| Coding | `beep/coding/` | Metadata, prompt context for Coding Assistant |
| Chat | `beep/chat/` | REPL, runner, slash commands, stream renderer |
| Agent | `beep/agent/` | LangGraph, tools, providers, subagents, bundles |
| Workspace | `beep/workspace/` | Detector, ignore, search, view, editing helpers |
| Context | `beep/context/` | Smart/auto context builders, windowing |
| Memory | `beep/memory/` | `.beep.md` loader |
| Rules | `beep/rules/` | AGENTS.md / `.beep/rules` layering |
| Skills | `beep/skills/` | Markdown skill packs |
| Plugins | `beep/plugins/` | Registry, runtime load |
| MCP | `beep/mcp/` | Client, presets, discovery, contracts |
| Templates | `beep/templates/` | Catalog, discovery, rendering, language plugins |
| Sessions | `beep/sessions/` | History, compaction, export |
| RAG | `beep/rag/` | Query helpers (CLI uses API client) |
| Code analysis | `beep/codeanalysis/` | Semgrep, architecture analyzers |
| Code index | `beep/codeindex/` | Tree-sitter symbols |
| Watcher | `beep/watcher/` | Watchdog integration |
| TUI | `beep/tui/` | Textual application |
| Publishing | `beep/publishing/` | Release channels, deploy adapters |
| Permissions | `beep/permissions/` | Sandbox modes |
| Hooks | `beep/hooks/` | Event hooks |
| Diagnostics | `beep/diagnostics/` | Health monitors |
| Linter | `beep/linter/` | Lint runner |
| Errors | `beep/errors/` | Parse/classify tool errors |
| Runtime | `beep/runtime/` | `WorkspaceRuntime`, capabilities |
| Commands | `beep/commands/` | Typer command implementations |

## WorkspaceRuntime (not on AppService)

[`beep/runtime/workspace.py`](../beep/runtime/workspace.py) caches immutable per-workspace aggregates:

- Project memory text
- Rules and skills resolution
- Plugin registry instance (when enabled)
- Used by chat and agent entrypoints

Clear cache in tests: `clear_workspace_runtime_cache()`.

## Extension points

| Mechanism | Discovery | Consumed by |
|-----------|-----------|-------------|
| Plugins | `~/.beepai/plugins`, `.beep/plugins`, `BEEP_PLUGINS_DIR` | REPL, agent tools |
| Skills | `~/.beepai/skills`, `.beep/skills` | REPL system prompt |
| Rules | `AGENTS.md`, `.beep/rules`, user rules | REPL / agent prompt |
| Hooks | `~/.beepai/hooks.json` | Hook manager events |
| MCP presets | `beep mcp presets`, `code.json` | Agent when `BEEP_MCP` enabled |

See per-feature [ENHANCEMENT_PLAN.md](ENHANCEMENT_PLAN.md) entries.
