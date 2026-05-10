# Agent Rules

This repository is standards-first.

- If a service implements an established standard protocol or API, its canonical surface must use that standard directly.
- `ai_middleware` is for Beep-specific, non-standard, helper, bootstrap, orchestration, or compatibility APIs only.
- Do not put canonical `MCP`, OpenAI-compatible, OAuth/OIDC discovery, or other standards-based surfaces under `ai_middleware` when a standards-compliant route exists.
- When a temporary compatibility seam is necessary, keep the standards-based route canonical and document the compatibility reason explicitly.
- Keep website/session-auth routes separate from application-token routes.
- Read [Beep.AI.Server/docs/ENGINEERING_IMPLEMENTATION_GUIDELINES.md](Beep.AI.Server/docs/ENGINEERING_IMPLEMENTATION_GUIDELINES.md) before structural changes.

## Clean Code And File Size Rules

- Always use clean code patterns and refactor while implementing; do not leave mixed responsibilities, duplication, or god-objects in place.
- Divide and conquer: when a feature grows, split it into smaller focused modules, services, adapters, or helpers before adding more behavior.
- No code file may exceed 500 lines.
- Treat roughly 300 lines as the split warning zone; do not wait until a file is already hard to review.
- If an existing file is already near or above 500 lines, do not keep growing it. Extract the new or adjacent responsibility first.

## Singleton Services Rule

All long-lived, stateful services must be singletons accessed through `AppService`.

- **Never** instantiate service classes directly outside `beep/app_service.py`.
- Always use `from beep.app_service import get_app_service` and access services through the registry.
- Example: `get_app_service().code_analysis.analyze_project(...)` not `CodeAnalysisService()`.
- Services currently in AppService: `code_analysis`, `bookmarks`, `tasks`, `permissions`, `hooks`, `language_registry`, `template_registry`, `api_client`, `mcp_client`, `smart_context`, `auto_context`, `chat_context`, `tree_sitter_parser`, `python_jedi`, `semble_index`, `plugin_registry`, `template_validator`, `rollback`, `standards_reviewer`.
- Keyed singletons (one per workspace/config): `watcher`, `api_client`, `mcp_client`, `smart_context`, `auto_context`, `chat_context`, `python_jedi`, `semble_index`, `plugin_registry`.
- If you add a new service class, register it in `AppService` immediately.

## Plan Execution And Todo Discipline

- Treat `.plans/README.md`, the phase documents under `.plans/PHASE_*.md`, and `MASTER-TODO-TRACKER.md` as the canonical execution backlog for Beep.AI.Code.
- Before broad implementation, refactor, or "continue" requests, read the phase index, the relevant phase document(s), and the master tracker, then continue from the next incomplete todo unless the user explicitly reprioritizes.
- When a phase is already marked in progress, prefer completing its open items before starting unrelated later-phase work unless blocked or redirected by the user.
- Every shipped implementation slice must update the relevant phase document and `MASTER-TODO-TRACKER.md` in the same change so phase status and task status stay synchronized.
- Do not mark a phase complete until its acceptance criteria and verification expectations are satisfied.
- Do not treat the plans as passive documentation; when the user asks for ongoing implementation, the default expectation is to advance the planned phases and their todo items, not just opportunistic local cleanup.

---

## Code-First Implementation

**Everything must be implemented as executable code and typed configuration, not just JSON config definitions.**

- JSON stores runtime state (user-created definitions, environment status, task results) — it is **never** the source of truth for behavior.
- Agent templates, system prompts, tool definitions, and framework mappings live in **Python modules** with type hints, tests, and imports.
- The `AgentDefinitionStore` (JSON) is a **registry/display layer** — it persists user-created instances but reads its built-in templates from `builtin_templates/` Python code.
- Adding a new agent type means: create a prompt file (`prompts/coding/my_agent.py`), a template definition (`templates/coding_templates.py`), and wire it through the resolver (`agent_definition_resolver.py`). Do not just add a JSON entry.
- Configuration that affects behavior (framework selection, tool policies, guardrails) must be validated at import time, not at JSON load time.
- If a feature can be expressed as Python code with tests, it must be. JSON is only for user-generated data that cannot be known at deploy time.

---

## Agent Framework Strategy

The system supports 4 frameworks — they are **not interchangeable**. Each has different capabilities:

| Framework | Capabilities | Best For | Packages Required |
|-----------|-------------|----------|-------------------|
| `native` | Direct inference, tool calling via inference service | Read-only agents, simple Q&A, code review | None (built-in) |
| `langgraph` | Stateful ReAct loop, memory, checkpoints, multi-turn | Most agents: coding, personal, enterprise assistants | `langgraph` |
| `deepagents` | Planning, sub-agent spawning, file system tools, deep research | Complex multi-step agents: bug fixer, refactoring, architecture | `deepagents` |
| `langchain` | Basic ReAct agent loop | Legacy compatibility | `langchain` |

### Default Framework Selection

**Use 2 frameworks by default** — this covers 95% of use cases without unnecessary dependencies:

1. **`langgraph`** — Primary framework for all agents that need tool use, memory, or multi-turn conversations. This is the default for coding assistants, personal assistants, and most enterprise agents.

2. **`native`** — For read-only agents that don't need an agent loop: code reviewer, compliance reviewer, architecture advisor, GitHub monitor. These agents analyze and report without executing tools.

### When to Use Each Framework

- **`native`**: Agent only reads and analyzes. No tool execution needed. Fastest, zero dependencies.
- **`langgraph`**: Agent uses tools, needs conversation memory, or runs multi-step workflows. The sweet spot.
- **`deepagents`**: Agent needs autonomous planning, sub-agent delegation, or deep file system operations. Only for complex coding agents.
- **`langchain`**: Legacy only. Prefer `langgraph` for new agents.

### Template Framework Assignment

Each template specifies its `recommended_framework` based on its complexity:

- **Coding agents** (coding_assistant, test_writer, bug_fixer, etc.) → `langgraph`
- **Read-only agents** (code_reviewer, architecture_advisor, compliance_reviewer) → `native`
- **Complex planning agents** (refactoring_agent, code_migration_agent) → `deepagents` (optional)
- **Personal assistants** (gateway, email/calendar, browser automator) → `langgraph`
- **Enterprise agents** (data_analyst, customer_support, incident_responder) → `langgraph`

### Resolver Behavior

The `AgentDefinitionResolver` resolves agent definitions at runtime:
- Reads `AgentDefinition` from the store
- Resolves `mcp_server_ids` → actual MCP server configs via `MCPServerManager`
- Resolves `model.provider_key` + `model.model_id` → runtime model reference
- Builds tool list from `tool_policy.allowed_categories` + resolved MCP tools
- Passes everything to the framework adapter

This bridges the gap between stored definitions and actual execution.

## Service Design Pattern

Every AI service (Agents, MCP, Data Sources, Text-to-Image, etc.) must follow this structure:

### Golden rule — one page, one business functionality

- **One route = one business concern.** Each page answers a single operator question (e.g. “which databases exist?”, “how is chunking configured for this collection?”, “what packages are installed?”). If the user could describe the screen with an **and** between two unrelated nouns (“databases **and** chunking”), it is two pages, not one.
- **Anti-pattern (do not do this):** Showing a **list of databases** (or RAG DB profiles, MCP servers, etc.) on the same page as **chunking type** / embedding strategy / other ingestion settings—those are different business capabilities; the list page is browse/registry; chunking belongs on collection config, pipeline, or chunk-template routes via submenu.
- **Never mix unrelated workflows on a single page.** Environment setup vs registry list vs a single config surface must each be their own route. If a screen tries to do two jobs, split it into two routes.
- **After the environment exists and is ready**, the service **Overview** is not a grab-bag: it shows the **primary result set** for that service—the registry/list of the main entities users manage (servers, agent definitions, RAG collections, etc.)—with **New**, row actions, and optional view toggles as defined elsewhere in this doc.
- **Every other capability** (workspace, runtime, analytics, chunking, import/sync, advanced settings, etc.) lives on **its own route** and is reached only through the **submenu** (`_section_nav.html` or equivalent local nav), not embedded as a second primary workflow on Overview.

### 1. Overview Page First
- The root route (`/service/`) is always the **Overview** page
- Shows environment setup wizard when env is NOT ready
- When env IS ready, shows the **primary list/registry** of the service's main entities (e.g., MCP Servers list, Agent Definitions list)—this is the **result set** for that service; do not replace it with unrelated panels
- Primary list includes: table/cards of items, **New** button (top-right), **Edit**/**Delete** actions per item
- Other functionality accessible via submenu buttons (`_section_nav.html`) only—not as duplicate or mixed primary content on Overview
- Uses `base_service.html` template with `env_status`, `service_info`, `service_setup`, `service_status`

### 2. Environment Gating
- All functionality pages pass `workspace_locked = not _is_env_ready()` to templates
- When locked, show a warning alert with link back to Overview
- `_is_env_ready()` checks `env_status.status == "ready"` AND `all_required_installed`
- Workspace page also shows locked state but remains accessible as a landing

### 3. One Functionality Per Page
- Each feature gets its own route and template
- Never mix **business** functionalities on one page (same as the **Golden rule**: one business capability per page; submenu for the next capability)
- Local navigation via `_section_nav.html` partial so users always know where to go for the next distinct task

### 4. Route Structure
```
/service/              → Overview (env setup + status)
/service/workspace/    → Workspace (gated behind env readiness)
/service/feature-a/    → Feature A page
/service/feature-b/    → Feature B page
/service/api/status    → API: env status
/service/api/create-env → API: create environment
/service/api/install-packages → API: install packages
```

### 5. Service Metadata
Each service defines three helper functions:
- `_get_service_info()` → name, icon, description, route, overview_endpoint, workspace_endpoint, local_nav_links
- `_get_service_setup()` → boundary_label, intro, cards, note, not_created_copy, ready_copy, packages_copy, install_note
- `_get_service_status()` → bridge report, counts, execution_surfaces

### 6. Template Conventions
- Extend `base.html` (NOT `base_service.html` for functionality pages)
- Include `{% include "ai_services/<service>/_section_nav.html" %}` after page header
- Page header pattern: service icon + name, description, breadcrumb nav
- Workspace locked alert pattern: warning with lock icon, message, "Go to Overview" button

### 7. Environment Gating in Templates
```jinja
{% if workspace_locked %}
<div class="alert alert-warning mt-3">
    <div class="d-flex align-items-start">
        <i class="bi bi-lock-fill fs-4 me-3 mt-1"></i>
        <div>
            <h5 class="alert-heading">Feature Locked</h5>
            <p class="mb-2">The environment is not ready. Complete setup on Overview.</p>
            <a href="{{ url_for('service.index') }}" class="btn btn-sm btn-warning">Go to Overview</a>
        </div>
    </div>
</div>
{% else %}
{# actual content #}
{% endif %}
```

---

## Key File Locations

### Routes
- Agent Framework: `Beep.AI.Server/app/routes/agents.py`
- MCP: `Beep.AI.Server/app/routes/mcp_page_routes.py` (page routes) + `mcp_api_routes.py` (API routes)

### Templates
- Base service layout: `templates/ai_services/base_service.html`
- Shared nav partial: `templates/ai_services/_partials/service_local_nav.html`
- Agents: `templates/ai_services/agents/`
- MCP: `templates/ai_services/mcp/`

### Environment Managers
- Agents: `app/services/utils/agents_environment.py` → `get_agents_env()`
- MCP: `app/services/utils/mcp_environment.py` → `get_mcp_env()`

### JS Namespace Pattern
- Each service has a `namespace.js` that defines the global `MCP` or `AGENTS` object
- API calls go through `api.js`
- Page-specific logic in separate files (e.g., `servers.js`, `templates.js`)

---

## Testing
- Tests live in `Beep.AI.Server/tests/`
- Use `monkeypatch` to mock environment managers and bridges
- Test both ready and not-ready states
- Run with: `python -m pytest tests/test_agents_routes.py -v`

---

## User Experience: Simple Default + Advanced Mode

Every process, form, and workflow must be **user-friendly by default** for non-technical users. Technical details, raw parameters, and low-level controls must be hidden behind an **Advanced** toggle.

### Core Rules
1. **Default view shows only what a normal user needs** — plain language, guided steps, sensible defaults
2. **Advanced mode is opt-in** — toggle/button labeled "Show Advanced" or "Advanced Options"
3. **Advanced mode reveals** — raw config fields, technical parameters, JSON editors, expert settings
4. **Never require advanced mode for normal workflows** — the default path must be complete and functional
5. **Remember user preference per session** — if a user enables advanced mode, keep it on while navigating the service

### Implementation Pattern

#### HTML Toggle
```jinja
<div class="d-flex justify-content-end mb-3">
    <button type="button" class="btn btn-sm btn-outline-secondary" id="btn-toggle-advanced">
        <i class="bi bi-gear-wide-connected me-1"></i>Show Advanced
    </button>
</div>
<div id="advanced-section" class="d-none">
    {# technical fields, raw config, JSON editors #}
</div>
```

#### JS Toggle (per service namespace)
```js
// In page JS or namespace
(function() {
    const btn = document.getElementById('btn-toggle-advanced');
    const section = document.getElementById('advanced-section');
    if (!btn || !section) return;
    const STORAGE_KEY = 'beep_advanced_<service>';
    if (sessionStorage.getItem(STORAGE_KEY) === '1') {
        section.classList.remove('d-none');
        btn.innerHTML = '<i class="bi bi-gear-wide me-1"></i>Hide Advanced';
    }
    btn.addEventListener('click', function() {
        const isAdvanced = section.classList.toggle('d-none');
        btn.innerHTML = isAdvanced
            ? '<i class="bi bi-gear-wide-connected me-1"></i>Show Advanced'
            : '<i class="bi bi-gear-wide me-1"></i>Hide Advanced';
        sessionStorage.setItem(STORAGE_KEY, isAdvanced ? '' : '1');
    });
})();
```

#### Page-Level Advanced Candidates
- **Overview/Setup**: Hide package version selectors, pip flags, env path overrides behind Advanced
- **Runtime**: Hide raw env vars, config file paths, debug flags behind Advanced
- **Providers**: Hide pip package names, version constraints, install flags behind Advanced
- **Shared Sources**: Hide raw connection strings, JSON config, API keys behind Advanced
- **Workspace**: Hide raw config exports, debug logs, internal IDs behind Advanced

### Labeling Conventions
- Toggle button: `Show Advanced` / `Hide Advanced`
- Section header: `Advanced Options`
- Tooltip on advanced fields: `Advanced: only change if you understand the implications`
- Warning banner in advanced sections: `These settings affect the underlying configuration. Incorrect values may break the service.`

---

## Multi-Item Display: Rows Default, Cards Optional

**All multi-item lists (agents, MCP servers, templates, providers, etc.) must default to a compact row/table view.** Card views are opt-in — users toggle to cards or expand a row to see a detail card popup.

### Core Rules
1. **Default view is always rows/table** — dense, scannable, shows key columns (name, status, framework, target, etc.)
2. **Card view is opt-in** — toggle button labeled "Show Cards" or expand icon (`+` / `bi-chevron-down`) on each row
3. **Row click or `+` opens a detail card** — popup/slide-over with full description, tags, metadata, and actions
4. **Remember user preference per session** — if a user switches to card view, keep it while navigating the service
5. **Mobile defaults to cards** — on small screens (< 768px), cards are acceptable as default since tables are unusable

### When to Use Each
- **Rows (default)**: Agents list, MCP servers, provider packs, templates, model registry, data sources
- **Cards (opt-in)**: When visual comparison is needed, when items have rich metadata (icons, descriptions, tags), or when user explicitly requests it
- **Detail popup**: Always available via `+` or row click — shows full card content without leaving the list

### Implementation Pattern

#### HTML Structure
```jinja
<div class="d-flex justify-content-between align-items-center mb-3">
    <h5 class="mb-0">Agents</h5>
    <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-outline-secondary" id="btn-toggle-view">
            <i class="bi bi-grid-3x3-gap me-1"></i>Show Cards
        </button>
        <a class="btn btn-sm btn-primary" href="..."><i class="bi bi-plus me-1"></i>New</a>
    </div>
</div>

<!-- Row view (default) -->
<div id="list-view" class="table-responsive">
    <table class="table table-dark table-hover align-middle">
        <thead>...</thead>
        <tbody id="list-body">
            <!-- Rows with expand action -->
        </tbody>
    </table>
</div>

<!-- Card view (hidden by default) -->
<div id="card-view" class="d-none row g-3">
    <!-- Cards populated by same data source -->
</div>

<!-- Detail popup (shown on row expand) -->
<div class="modal fade" id="detail-modal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content bg-dark border-secondary">
            <div class="modal-body" id="detail-content">
                <!-- Full card content injected here -->
            </div>
        </div>
    </div>
</div>
```

#### JS Toggle
```js
(function() {
    const btn = document.getElementById('btn-toggle-view');
    const listView = document.getElementById('list-view');
    const cardView = document.getElementById('card-view');
    if (!btn || !listView || !cardView) return;

    const STORAGE_KEY = 'beep_view_<service>';
    const isCard = sessionStorage.getItem(STORAGE_KEY) === 'cards';
    if (isCard) {
        listView.classList.add('d-none');
        cardView.classList.remove('d-none');
        btn.innerHTML = '<i class="bi bi-list-ul me-1"></i>Show Rows';
    }

    btn.addEventListener('click', function() {
        const showingCards = listView.classList.toggle('d-none');
        cardView.classList.toggle('d-none');
        btn.innerHTML = showingCards
            ? '<i class="bi bi-list-ul me-1"></i>Show Rows'
            : '<i class="bi bi-grid-3x3-gap me-1"></i>Show Cards';
        sessionStorage.setItem(STORAGE_KEY, showingCards ? 'cards' : '');
    });
})();
```

#### Row Expand to Detail
```js
// On row "+" click or row click
function showDetail(agentId) {
    fetch('/agents/api/agents/' + agentId)
        .then(r => r.json())
        .then(data => {
            const a = data.agent;
            document.getElementById('detail-content').innerHTML = buildDetailCard(a);
            new bootstrap.Modal(document.getElementById('detail-modal')).show();
        });
}
```

### Labeling Conventions
- Toggle button: `Show Cards` / `Show Rows`
- Expand icon: `bi-chevron-down` or `bi-plus-circle` on each row
- Detail modal title: item name with close button
- Empty state: same message for both views
