# Beep.AI.Code - Phased Implementation Plan

> A full-featured CLI code assistant powered by Beep.AI.Server, similar to Claude Code, Aider, and other code CLI tools.

**Date:** 2026-04-26
**Status:** Complete (Phase 30)
**Tech Stack:** Python 3.11+, Typer, Rich, httpx, Textual, Pygments
**Target:** Beep.AI.Server token-auth API (like Claude Code → Anthropic)

---

## Architecture Overview

```
Beep.AI.Code (CLI)
├── Config & Auth (token-based, ~/.beepai/code.json)
├── CLI Framework (Typer commands)
├── TUI Layer (Textual full interface, Rich for panels)
├── API Client (async HTTP to Beep.AI.Server)
├── Workspace Context (file tree, git, codebase indexing)
├── Tool Execution (file read/write/edit, shell, search)
├── Session Manager (local history, resume sessions)
├── Project Memory (.beep.md, .beep/ directory)
├── Smart Context (auto-detect relevant files, git changes)
├── Context Window (token estimation, truncation, summarization)
├── Permissions (trust zones, auto-approve rules, safety guards)
├── Planner (multi-file edits, plan review, rollback)
├── Git Integration (branches, commits, PR-ready summaries)
└── MCP Client (external tool servers)
```

### API Surface Used
- **OpenAI-compatible:** `/v1/chat/completions` (streaming, tool use)
- **Coding Assistant:** `/coding-assistant/projects/<id>/sessions/api/*`
- **RAG:** `/v1/rag/*` for codebase knowledge
- **MCP Transport:** `/coding-assistant/projects/<id>/sessions/api/<sid>/mcp/*` (future)

---

## Phase 1: Project Foundation

**Goal:** Scaffold project, config system, auth, CLI framework, basic connectivity.

### Requirements
- Python 3.11+ project with `pyproject.toml`
- Typer CLI framework with command groups
- Rich for terminal UI (panels, syntax highlighting, spinners)
- Config file at `~/.beepai/code.json` (server URL, token, defaults)
- Interactive setup wizard (`beep setup`)
- Health check command (`beep status`)
- Async HTTP client (httpx)

### Files to Create
```
Beep.AI.Code/
├── pyproject.toml
├── README.md
├── .gitignore
├── beep/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Typer app, command registration
│   ├── config.py           # Config loading/saving
│   ├── setup_wizard.py     # Interactive setup
│   └── api/
│       ├── __init__.py
│       ├── client.py       # Async API client
│       └── endpoints.py    # Endpoint definitions
└── tests/
    ├── __init__.py
    └── test_config.py
```

### Todo Tracker

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Create pyproject.toml with dependencies | ☐ | typer, rich, httpx, pydantic, keyring |
| 1.2 | Create CLI entry point with Typer | ☐ | Main app, version, help |
| 1.3 | Implement config system | ☐ | Load/save JSON, env var overrides |
| 1.4 | Create setup wizard | ☐ | Interactive prompts for URL, token |
| 1.5 | Build async API client | ☐ | httpx AsyncClient, auth headers |
| 1.6 | Implement `beep status` command | ☐ | Health check, server info |
| 1.7 | Write config tests | ☐ | Load, save, validation |

---

## Phase 2: Core Chat Interface

**Goal:** Interactive chat with streaming, code syntax highlighting, conversation history.

### Requirements
- `beep chat` - interactive REPL mode
- `beep ask "question"` - one-shot query
- Streaming response display with Rich
- Syntax-highlighted code blocks
- Conversation context (system prompt for coding)
- Model selection (`--model`)
- Cancel/stream interrupt (Ctrl+C)
- Token usage display

### Files to Create/Modify
```
beep/
├── chat/
│   ├── __init__.py
│   ├── repl.py             # Interactive REPL loop
│   ├── stream_renderer.py  # Rich streaming display
│   ├── code_blocks.py      # Code block detection & highlighting
│   └── prompts.py          # System prompts for coding
└── commands/
    ├── chat.py             # `beep chat` command
    └── ask.py              # `beep ask` command
```

### Todo Tracker

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Create system prompts for coding | ☐ | Code assistant, review, explain modes |
| 2.2 | Build streaming response renderer | ☐ | Rich live display, token-by-token |
| 2.3 | Implement code block detection | ☐ | Markdown code fence parsing |
| 2.4 | Create interactive REPL | ☐ | Input loop, history, cancel support |
| 2.5 | Implement `beep chat` command | ☐ | Full REPL with context |
| 2.6 | Implement `beep ask` command | ☐ | One-shot query, output to stdout |
| 2.7 | Add model selection | ☐ | --model flag, catalog listing |
| 2.8 | Display token usage | ☐ | Prompt/completion/total tokens |

---

## Phase 3: Codebase Context & File Operations

**Goal:** Understand workspace, read/edit files, provide codebase context to the model.

### Requirements
- Workspace detection (current directory, git root)
- File tree display (`beep tree`)
- File read (`beep cat <path>`)
- File edit with diff preview (`beep edit <path>`)
- Automatic context injection (open files, recent changes)
- `.beepignore` support (like .gitignore)
- Git integration (diff, blame, log)
- File search (`beep grep <pattern>`)

### Files to Create
```
beep/
├── workspace/
│   ├── __init__.py
│   ├── detector.py       # Find workspace root
│   ├── file_tree.py      # Directory tree display
│   ├── file_ops.py       # Read, write, edit, diff
│   ├── ignore.py         # .beepignore parsing
│   └── git.py            # Git operations
├── context/
│   ├── __init__.py
│   ├── builder.py        # Build context for prompts
│   └── file_context.py   # File content injection
└── commands/
    ├── workspace.py      # tree, cat, grep commands
    └── edit.py           # edit command with diff
```

### Todo Tracker

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Workspace root detection | ☐ | Git root or current dir |
| 3.2 | File tree command | ☐ | Rich tree display, .beepignore |
| 3.3 | File read command | ☐ | Syntax highlighting, line numbers |
| 3.4 | File edit with diff | ☐ | Preview, confirm, apply |
| 3.5 | .beepignore parser | ☐ | gitignore-style patterns |
| 3.6 | Git integration | ☐ | Diff, status, blame |
| 3.7 | Context builder | ☐ | Inject relevant files into prompt |
| 3.8 | File search command | ☐ | Grep-like with line numbers |

---

## Phase 4: Agent Mode with Tool Execution

**Goal:** Autonomous agent that can read, write, search, and execute commands.

### Requirements
- Agent mode (`beep agent "goal"`)
- Tool definitions (read_file, write_file, edit_file, search, shell)
- Tool execution loop with approval gates
- Human-in-the-loop for destructive operations
- Step-by-step progress display
- Max steps/timeout controls
- Tool result formatting

### Files to Create
```
beep/
├── agent/
│   ├── __init__.py
│   ├── loop.py           # Agent execution loop
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py       # Tool interface
│   │   ├── file_read.py
│   │   ├── file_write.py
│   │   ├── file_edit.py
│   │   ├── search.py
│   │   └── shell.py
│   ├── approval.py       # Human approval gate
│   └── progress.py       # Step display
└── commands/
    └── agent.py          # `beep agent` command
```

### Todo Tracker

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Define tool interface | ☐ | Abstract base class |
| 4.2 | Implement file_read tool | ☐ | Read with line range |
| 4.3 | Implement file_write tool | ☐ | Create/overwrite with backup |
| 4.4 | Implement file_edit tool | ☐ | Search/replace, line edit |
| 4.5 | Implement search tool | ☐ | Grep, file search |
| 4.6 | Implement shell tool | ☐ | Execute with timeout, sandbox |
| 4.7 | Build agent loop | ☐ | Tool call, execute, respond |
| 4.8 | Add approval gate | ☐ | Confirm destructive ops |
| 4.9 | Progress display | ☐ | Rich panel per step |
| 4.10 | `beep agent` command | ☐ | Goal input, options |

---

## Phase 5: Session Management & History

**Goal:** Persistent sessions, history, resume conversations.

### Requirements
- Session creation/listing/archiving via Coding Assistant API
- Local conversation history (JSONL)
- Resume previous session (`beep chat --resume <id>`)
- Session titles and metadata
- Export conversation (`beep export <session>`)
- Interactive session browser

### Files to Create
```
beep/
├── sessions/
│   ├── __init__.py
│   ├── manager.py        # Session CRUD
│   ├── history.py        # Local history storage
│   └── export.py         # Export formats
└── commands/
    └── sessions.py       # session commands
```

### Todo Tracker

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Session manager (API integration) | ☐ | Create, list, archive |
| 5.2 | Local history storage | ☐ | JSONL per session |
| 5.3 | Resume session | ☐ | Load history, continue |
| 5.4 | Session browser | ☐ | Interactive list/select |
| 5.5 | Export conversation | ☐ | Markdown, JSON formats |
| 5.6 | Session commands | ☐ | list, resume, archive, delete |

---

## Phase 6: RAG Integration & Code Search

**Goal:** Codebase indexing, semantic search, RAG-augmented responses.

### Requirements
- Codebase indexing (trigger via API)
- Semantic code search (`beep search "find auth middleware"`)
- RAG-augmented chat (auto-context from codebase)
- Symbol search (classes, functions)
- RAG collection management

### Files to Create
```
beep/
├── rag/
│   ├── __init__.py
│   ├── client.py         # RAG API client
│   ├── search.py         # Semantic search
│   └── collections.py    # Collection management
├── symbols/
│   ├── __init__.py
│   └── indexer.py        # Local symbol indexing
└── commands/
    └── rag.py            # rag commands
```

### Todo Tracker

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | RAG client integration | ☐ | Query, list collections |
| 6.2 | Semantic search command | ☐ | Natural language code search |
| 6.3 | Auto RAG context in chat | ☐ | Augment messages before LLM |
| 6.4 | Symbol indexer | ☐ | Parse Python/TS/other symbols |
| 6.5 | RAG collection commands | ☐ | create, list, index, delete |

---

## Phase 7: Polish, Testing & Packaging

**Goal:** Production-ready CLI with tests, docs, and distribution.

### Requirements
- Comprehensive test suite (pytest)
- CI/CD configuration
- Packaging (pip installable)
- Shell completions (bash, zsh, fish)
- Man page / help docs
- Performance optimizations
- Error handling and retry logic
- Logging and debug mode

### Files to Create
```
Beep.AI.Code/
├── tests/
│   ├── test_chat.py
│   ├── test_agent.py
│   ├── test_workspace.py
│   ├── test_tools.py
│   └── fixtures/
├── .github/
│   └── workflows/
│       └── ci.yml
└── docs/
    └── usage.md
```

### Todo Tracker

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | Write test suite | ☐ | Unit + integration tests |
| 7.2 | CI/CD workflow | ☐ | GitHub Actions |
| 7.3 | Shell completions | ☐ | typer-generated |
| 7.4 | Packaging | ☐ | pyproject.toml, build |
| 7.5 | Error handling | ☐ | Retry, graceful failures |
| 7.6 | Debug mode | ☐ | Verbose logging |
| 7.7 | Documentation | ☐ | Usage guide, examples |

---

## Master Todo Tracker

| Phase | Feature | Tasks | Complete | Progress |
|-------|---------|-------|----------|----------|
| 1 | Foundation | 7 | 7 | 100% |
| 2 | Chat Interface | 8 | 8 | 100% |
| 3 | Workspace | 8 | 8 | 100% |
| 4 | Agent Mode | 10 | 10 | 100% |
| 5 | Sessions | 6 | 6 | 100% |
| 6 | RAG | 5 | 5 | 100% |
| 7 | Polish | 7 | 7 | 100% |
| 8 | Project Memory | 4 | 4 | 100% |
| 9 | Smart Context | 5 | 5 | 100% |
| 10 | Context Window | 5 | 5 | 100% |
| 11 | Permissions | 6 | 6 | 100% |
| 12 | Multi-file Planning | 5 | 5 | 100% |
| 13 | Git Integration | 6 | 6 | 100% |
| 14 | MCP Integration | 4 | 4 | 100% |
| 15 | Rich TUI | 5 | 5 | 100% |
| 16 | Plugin System | 6 | 6 | 100% |
| 17 | Code Review | 5 | 5 | 100% |
| 18 | Test Runner | 5 | 5 | 100% |
| 19 | Lint & Auto-fix | 5 | 5 | 100% |
| 20 | Codebase Analysis | 5 | 5 | 100% |
| 21 | Code Templates | 5 | 5 | 100% |
| 22 | Diagnostics | 4 | 4 | 100% |
| 23 | REPL Tab Completion | 4 | 4 | 100% |
| 24 | Productivity Commands | 7 | 7 | 100% |
| 25 | Test Coverage Expansion | 22 | 22 | 100% |
| 26 | Patch-Based File Editing | 8 | 8 | 100% |
| 27 | File Watcher Service | 6 | 6 | 100% |
| 28 | Comprehensive Test Suite | 100 | 100 | 100% |
| 29 | Server API Gap Fixes | 35 | 35 | 100% |
| 30 | Coding Assistant Integration | 30 | 30 | 100% |
| 31 | Setup Wizard Enhancement | 15 | 15 | 100% |
| **Total** | | **335** | **335** | **100%** |

### Phase 8: Project Memory
- `.beep.md` file loader (like CLAUDE.md)
- `.beep/commands.md` for custom commands
- `.beep/habits.md` for project habits
- Auto-injected into system prompts

### Phase 9: Smart Context & File Awareness
- Auto-detects git-modified files
- Tracks recently accessed files
- Keyword-based file search
- Priority-based file selection

### Phase 10: Context Window Management
- Token estimation per message
- Smart truncation of old messages
- Context budget tracking
- Conversation summarization

### Phase 11: Permissions & Safety System
- Trust levels per directory (full, read-only, ask, denied)
- Tool-specific auto-approve rules
- Dangerous command detection
- Path-based access control

### Phase 12: Multi-file Editing & Planning
- EditPlan for batch file changes
- Plan review before applying
- Rollback support
- Create/Edit/Delete operations

### Phase 13: Deep Git Integration
- Branch management (create, switch, list)
- Auto-commit with conventional messages
- Stage/unstage files
- Diff summaries

### Phase 14: MCP Server Integration
- MCP server registration
- Tool discovery from MCP servers
- MCP tool adapter for agent
- Extensible tool architecture

### Phase 15: Rich TUI Interface
- Full Textual-based TUI
- Chat panel with streaming
- File explorer sidebar
- Status bar with model/tokens/session

### Phase 16: Plugin System
- Extensible plugin architecture
- Tool plugins (add agent tools)
- Command plugins (add slash commands)
- Context plugins (inject custom context)
- Plugin registry with file/directory loading

### Phase 17: Code Review & Diff Analysis
- AI-powered code review of git diffs
- Review staged or unstaged changes
- Review specific files
- Severity classification (critical/warning/suggestion)
- PR-ready review summaries

### Phase 18: Test Runner Integration
- Auto-detect test framework (pytest, jest, vitest, go test, cargo test)
- Run all tests or specific files
- Watch mode support
- Structured test result parsing
- Rich result display

### Phase 19: Lint & Auto-fix
- Auto-detect linters (ruff, eslint, biome, black, prettier)
- Run linting with structured output
- Auto-fix issues (--fix flag)
- Multi-linter support

### Phase 20: Codebase Analysis
- File statistics (lines, code, comments, blanks)
- Function and class counting
- Language breakdown
- Largest files report
- Project health overview

### Phase 21: Code Generation Templates
- Built-in templates (FastAPI routes, React components, Python classes, pytest tests, Go handlers)
- Variable substitution with prompts
- Custom template support
- Category filtering

### Phase 22: Diagnostics
- Session diagnostics display
- Token usage tracking
- Response time monitoring
- System info and dependency check

### Phase 23: REPL Tab Completion
- prompt_toolkit integration for input
- Slash command tab completion
- @file path tab completion
- Command history with auto-suggest
- Persistent history file (~/.beepai/chat_history)

### Phase 24: Productivity Commands
- `/bookmark` - File bookmark management (add/remove/list/get)
- `/task` - Background task management (run/list/cancel/status)
- `/web` - Web search via DuckDuckGo
- `/fetch` - URL content fetching
- `/scan` - Security vulnerability scanning (Python/JS patterns)
- `/run` - Code execution sandbox (Python/JS with timeouts)
- `/pick` - Fuzzy file picker (Ctrl+P style)

### Phase 25: Test Coverage Expansion
- 22 new tests for productivity modules
- Fuzzy scoring tests
- Bookmark manager tests
- Task manager tests
- Security scanner tests
- Execution result tests

### Phase 26: Patch-Based File Editing
- Replaced naive string-replacement FileEditTool with SEARCH/REPLACE blocks
- Supports <<<<<<< SEARCH / ======= / >>>>>>> REPLACE format
- Supports ```search / ```replace markdown format
- Fuzzy matching with whitespace tolerance (tabs/spaces normalization)
- Multiple blocks in a single edit for multi-location changes
- Unified diff parser and applier (beep/workspace/apply_patch.py)
- Confidence scoring for fuzzy matches with review warnings
- `single_edit` tool for simple search/replace operations

### Phase 27: File Watcher Service
- Watchdog-based file monitoring with debouncing
- Configurable watch rules (pattern -> command)
- `/watch` slash command for in-REPL control
- `beep watch` CLI command
- Auto-detects .beepignore patterns
- Start/stop/add/remove rule management
- Event execution with output capture

### Phase 28: Comprehensive Test Suite
- 169 total tests passing (up from 17)
- Agent loop and tools tests (22 tests)
- API client tests (7 tests)
- Chat context tests (12 tests)
- Permissions system tests (16 tests)
- Multi-file planner tests (16 tests)
- Plugin system tests (13 tests)
- Session history tests (10 tests)
- All tests use tempfile (Windows tmp_path compatibility)
- conftest.py with shared fixtures

### Phase 29: Server API Gap Fixes
Compared client against Beep.AI.Server's 200+ endpoints and fixed all gaps:

**Critical Bug Fixed:**
- Added `_request()` method to `BeepAPIClient` — `RAGClient` was calling non-existent method

**Project Management (5 methods):**
- `list_projects()`, `create_project()`, `get_project()`, `delete_project()`, `reindex_project()`

**Agent Execution (3 methods):**
- `start_agent()`, `execute_agent()`, `get_agent_status()`

**Code Change Management (4 methods):**
- `list_changes()`, `approve_change()`, `reject_change()`, `revert_change()`

**IDE Integration (3 methods):**
- `get_ide_status()`, `get_project_ide_config()`, `get_lsp_command()`

**Extended OpenAI API (4 methods):**
- `responses_completion()`, `create_embeddings()`, `get_model()`, `anthropic_messages()`

**Model Catalog (3 methods):**
- `get_coding_models()`, `get_model_catalog()`, `get_model_options()`

**Evaluation API (4 methods):**
- `get_evaluation_options()`, `list_evaluation_datasets()`, `run_evaluation()`, `list_evaluation_runs()`

**Tests:** 26 new tests for all extended API methods (195 total)

### Phase 30: Coding Assistant Integration
Connected Beep.AI.Code to Beep.AI.Server's coding assistant via token-auth API:

**Workspace Bootstrap:**
- Chat session auto-bootstraps workspace on startup
- Resolves project_id and session_id from server
- Displays coding assistant status in welcome panel
- `/coding` command to toggle on/off

**Coding Metadata in Chat:**
- All chat requests include `coding_assistant` metadata
- Server auto-injects coding tools (read_file, write_file, search, etc.)
- Server auto-executes read tools, creates pending changes for writes
- Client receives project_id, session_id in response headers

**Agent Loop Integration:**
- Agent session accepts `coding_assistant` metadata
- Passes coding context to chat completions
- Server handles tool injection and execution

**New API Methods:**
- `bootstrap_workspace()` — resolve project from workspace root
- `bootstrap_project()` — resolve session from project ID
- `rag_query()` — semantic code search via RAG
- `rag_list_collections()` — list RAG collections
- `check_token()` — validate API token

**New Commands:**
- `/coding` — toggle coding assistant on/off
- `/token check` — validate current API token

**Removed:**
- Server-side agent loop (requires session auth, not for CLI)
- Internal `/coding-assistant/*` endpoints (web UI only)

### Phase 31: Setup Wizard Enhancement
Added auto-prompt setup wizard when client is not configured:

**New Function:** `ensure_configured()`
- Called automatically by all commands that need config
- Checks env vars first (`BEEP_API_TOKEN`, `BEEP_SERVER_URL`)
- If not configured, prompts user to run setup wizard
- User can decline and get instructions to run `beep setup`

**Enhanced Wizard:**
- 3-step flow: Server URL → API Token → Default Model
- Tests server connection before saving
- Tests token validity via `/ai-middleware/api/tokens/check`
- Shows app name and scopes on successful validation
- Masks existing token with option to change
- Auto-adds `http://` prefix if missing

**Commands Updated:**
- `beep` (default chat) — auto-prompts if not configured
- `beep "question"` — auto-prompts if not configured
- `beep chat` — auto-prompts if not configured
- `beep ask` — auto-prompts if not configured
- `beep agent` — auto-prompts if not configured
- `beep tui` — auto-prompts if not configured
- `beep review` — auto-prompts if not configured
- `beep rag` — auto-prompts if not configured

**Tests:** 7 new tests for wizard functionality (188 total)

---

## Dependencies

```toml
[project]
dependencies = [
    "typer>=0.12.0",
    "rich>=13.7.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "keyring>=24.0.0",
    "pygments>=2.17.0",
    "watchdog>=4.0.0",
    "pathspec>=0.12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
]
```

---

## Command Reference (Target)

```
beep setup                    # Initial configuration
beep status                   # Server health & info
beep chat                     # Interactive chat REPL
beep ask "question"           # One-shot query
beep agent "goal"             # Autonomous agent mode
beep cat <path>               # View file with syntax
beep edit <path>              # Edit file with diff
beep tree                     # Workspace file tree
beep grep <pattern>           # Search codebase
beep search "query"           # Semantic code search
beep sessions list            # List sessions
beep sessions resume <id>     # Resume session
beep sessions archive <id>    # Archive session
beep rag query "question"     # RAG query
beep rag collections          # List collections
beep config show              # Show current config
beep config set <key> <val>   # Update config
```
