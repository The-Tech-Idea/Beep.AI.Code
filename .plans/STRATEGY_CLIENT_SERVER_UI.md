# Beep.AI — Client/Server Architecture Strategy

> **Created:** 2026-06-16  
> **Status:** Strategic shift — separating UI responsibilities from backend

---

## The Shift

```
BEFORE:  Beep.AI.Server had everything (backend + web UI + admin panel)
         Beep.AI.Code was CLI-only

AFTER:   Beep.AI.Server = pure backend API provider (no user-facing UI)
         Beep.AI.Code = the desktop app users see (professional agent UI)
```

## Why This Makes Sense

| Concern | Before | After |
|---------|--------|-------|
| LLM inference | ✅ Server | ✅ Server (unchanged) |
| RAG / document search | ✅ Server | ✅ Server (unchanged) |
| MCP servers | ✅ Server | ✅ Server (unchanged) |
| Agent runtime | ✅ Server | ✅ Server (unchanged) |
| Web admin UI | ⚠️ On server (mixed) | ➡️ Moves to Code app |
| End-user chat UI | ❌ CLI only | ➡️ Professional desktop UI |
| Setup wizard | ⚠️ Server web page | ➡️ Desktop app first-run flow |
| Profile management | ❌ None | ➡️ Desktop app, saved locally |

---

## The Two Repos

### Beep.AI.Server — "The Engine"
```
What it does:
  ✅ Hosts LLM models (llama.cpp, vLLM, MLX)
  ✅ Runs RAG pipelines (11 providers)
  ✅ Manages MCP servers (discovery, tools, OAuth)
  ✅ Executes agent frameworks (LangGraph, DeepAgents, native)
  ✅ Handles auth (JWT, API tokens, OAuth2, LDAP)
  ✅ Serves API endpoints (/v1/*, /v1/api/*)

What it does NOT do:
  ❌ No user-facing web UI (moved to Code)
  ❌ No profile management (moved to Code)
  ❌ No setup wizard pages (API-only)
  ❌ No chat UI rendering
```

### Beep.AI.Code — "The Experience"
```
What it does:
  ✅ Professional desktop agent UI (WPF + Blazor hybrid)
  ✅ Profile-driven onboarding (Simple Service Generator)
  ✅ Agent chat with file references, citations, code previews
  ✅ Local agent that orchestrates server tasks
  ✅ Session persistence (conversations saved locally)
  ✅ Settings management (profiles, preferences, API connection)
  ✅ First-run setup wizard → auto-configures server connection

What it does NOT do:
  ❌ No LLM inference (delegates to Server)
  ❌ No RAG indexing (delegates to Server)
  ❌ No MCP server hosting (delegates to Server)
```

---

## The Local Agent Concept

Beep.AI.Code runs a local agent on the user's machine that:

```
User types: "Review my auth module for security issues"
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              LOCAL AGENT (Beep.AI.Code)              │
│                                                     │
│  1. Reads project files (filesystem access)         │
│  2. Sends to Server: "Review auth.py for security"  │
│  3. Server runs code review agent                   │
│  4. Local agent receives results                    │
│  5. Local agent shows results with file links       │
│  6. User clicks "Fix it"                            │
│  7. Local agent orchestrates fix via Server         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

The local agent is NOT the AI — it's the orchestrator. It:
- Reads local files
- Dispatches tasks to Server agents
- Manages conversation context
- Handles tool approvals (file write, shell commands)
- Renders results in the UI

---

## Tech Stack Decision

| Layer | Technology | Why |
|-------|-----------|-----|
| **Desktop shell** | .NET 9 WPF | Existing, Material Design, Windows native |
| **Web views** | Blazor Hybrid (WebView2) | Embed Blazor components in WPF for rich chat UI |
| **Chat UI** | Blazor (reuse existing `Chat.razor`) | Already built, modern, responsive |
| **Agent runtime** | Python (existing beep/ CLI) | Embedded via Python.NET or subprocess |
| **Server comms** | httpx (async HTTP) | Already in beep/api/client.py |
| **Local storage** | SQLite + JSON | Sessions, settings, profile data |
| **Theming** | Material Design + profile CSS vars | Per-profile color schemes |

### Why WPF + Blazor Hybrid?

- WPF gives us native Windows integration (tray icon, notifications, file associations)
- Blazor Hybrid gives us the existing rich chat UI from `Beep.AI.Clients.WebUI`
- We don't throw away existing work — the `Chat.razor` page is already production-quality
- Material Design themes are already wired in the WPF project

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Beep.AI.Code Desktop App                       │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   WPF Shell     │  │  Blazor WebView  │  │  Python Agent  │  │
│  │                 │  │                  │  │  (subprocess)  │  │
│  │ • Window mgmt   │  │ • Chat UI        │  │ • File ops     │  │
│  │ • Tray icon     │  │ • Setup wizard   │  │ • Context      │  │
│  │ • Notifications │  │ • Settings pages │  │ • Orchestration│  │
│  │ • Native menus  │  │ • Profile picker │  │ • Tool approval│  │
│  │ • File assoc    │  │ • Agent panel    │  │                │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬────────┘  │
│           │                    │                     │           │
│           └────────────────────┼─────────────────────┘           │
│                                │                                 │
│                    ┌───────────▼──────────┐                      │
│                    │    Local Storage     │                      │
│                    │  SQLite + JSON files │                      │
│                    │  ~/.beepai/profiles/ │                      │
│                    └──────────────────────┘                      │
│                                │                                 │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
                    HTTP (REST + SSE streaming)
                                 │
┌────────────────────────────────▼─────────────────────────────────┐
│                    Beep.AI.Server (API)                           │
│                                                                  │
│  /v1/chat/completions     → LLM chat                             │
│  /v1/rag/search           → Document search                      │
│  /v1/api/*                  → Platform extensions                   │
│  /simple/api/*             → Simple Service Generator API        │
│                                                                  │
│  Backend services: LLM, RAG, MCP, Agents, Auth, Scheduler        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Profile → UI Mapping

When the app starts, it loads the user's profile and adapts the UI:

| Profile | Shell Theme | Default Tab | Sidebar Shows |
|---------|------------|-------------|---------------|
| Team Lead (Dev) | Dark code theme | Agent Chat | Agents, Reviews, Project files |
| Business Analyst | Light document theme | Document Search | Recent searches, Upload |
| Team Lead (Biz) | Professional theme | Assistant Chat | Assistants, Documents |
| Content Creator | Creative theme | Content Studio | Image history, Voice library |
| Student | Friendly theme | Simple Chat | Nothing (minimal) |
| Developer | Dark code theme | Full admin | All services |
| Solo Founder | Builder theme | App Builder | Build progress, Project |
| IT Admin | Enterprise theme | Dashboard | Monitoring, Users, Config |

### Theme Tokens (per profile)

```css
/* Team Lead (Dev) — Dark code theme */
--app-bg: #0d1117;
--sidebar-bg: #161b22;
--accent: #58a6ff;
--chat-user-bg: #1a2332;
--chat-assistant-bg: #0d1117;
--code-bg: #0d1117;
--border: #30363d;

/* Business Analyst — Light document theme */
--app-bg: #ffffff;
--sidebar-bg: #f6f8fa;
--accent: #0969da;
--chat-user-bg: #e8f0fe;
--chat-assistant-bg: #ffffff;
--code-bg: #f6f8fa;
--border: #d0d7de;

/* Content Creator — Creative theme */
--app-bg: #1a1a2e;
--sidebar-bg: #16213e;
--accent: #e94560;
--chat-user-bg: #0f3460;
--chat-assistant-bg: #1a1a2e;
--code-bg: #16213e;
--border: #533483;
```

---

## Startup Flow

```
App starts
  │
  ├─ Check for saved profile in ~/.beepai/profiles/active.json
  │
  ├─ Profile found?
  │   │
  │   ├─ YES → Skip wizard → Load profile → Show profile UI
  │   │         • Theme applied
  │   │         • Last session restored
  │   │         • Server connection verified
  │   │
  │   └─ NO  → Show setup wizard
  │            • Hardware detection
  │            • Profile picker
  │            • Server connection (auto-detect or manual)
  │            • Questions → Create All
  │            • Save profile → Show profile UI
  │
  └─ Server unreachable?
      → Show offline banner
      → Enable local-only features (file browsing, settings)
      → "Reconnect" button
```

---

## Migration Path

### Phase 1: Foundation (Weeks 1-2)
- [ ] Add profile persistence to Beep.AI.Code (`~/.beepai/profiles/`)
- [ ] Wire up WPF shell with Blazor WebView2
- [ ] Embed existing `Chat.razor` in WebView2
- [ ] Add profile-based theme switching
- [ ] Skip wizard on restart with saved profile

### Phase 2: Agent UI (Weeks 3-4)
- [ ] Agent panel: switch between agents in sidebar
- [ ] File reference links in chat (click to open in editor)
- [ ] Code review inbox
- [ ] Tool approval UI (confirm file writes, shell commands)
- [ ] Session history with search

### Phase 3: Profile Pages (Weeks 5-6)
- [ ] Business Analyst: Document search page
- [ ] Content Creator: Image/voice generation page
- [ ] Solo Founder: App builder page
- [ ] IT Admin: Dashboard page

### Phase 4: Polish (Weeks 7-8)
- [ ] Tray icon + notifications
- [ ] Keyboard shortcuts
- [ ] File association (.beep project files)
- [ ] Auto-update
- [ ] Offline mode improvements
