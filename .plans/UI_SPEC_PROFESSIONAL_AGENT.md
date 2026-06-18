# Beep.AI.Code — Professional Agent UI Specification

> **Based on:** Cursor, Copilot Chat, Windsurf, Claude Code industry analysis  
> **Technology:** WPF shell + Blazor Hybrid (WebView2) + Material Design  
> **Reuses:** Existing `Beep.AI.Clients.WebUI/Chat.razor` as foundation

---

## Industry UI Patterns (What We're Matching)

After analyzing the top 5 AI coding tools, here are the UI patterns that matter:

### 1. Three-Panel Layout (Cursor, Windsurf, Copilot)

```
┌──────────┬───────────────────────┬──────────┐
│          │                       │          │
│  AGENT   │    MAIN CONTENT       │  CONTEXT │
│  PANEL   │                       │  PANEL   │
│          │    (Chat or Editor)   │          │
│  ─────   │                       │  ─────   │
│  Agent 1 │                       │  Files   │
│  Agent 2 │                       │  Symbols │
│  Agent 3 │                       │  Context │
│          │                       │  Rules   │
│  ─────   │                       │          │
│  Sessions│                       │          │
│  History │                       │          │
│          │                       │          │
│  ─────   │                       │          │
│  Settings│                       │          │
│          │                       │          │
└──────────┴───────────────────────┴──────────┘
```

This is the standard. Every major tool uses it. We will too.

### 2. Inline Code Rendering (All tools)

Code blocks in chat responses are syntax-highlighted, with:
- File path header: `📄 src/auth/login.ts`
- Line numbers
- Apply/Diff buttons
- Copy button

### 3. Agent Awareness (Cursor, Windsurf)

The agent shows what it's doing:
- "🔍 Reading auth.py..."
- "✏️ Editing login.ts:42-67"
- "🔧 Running pytest..."
- "✅ Done — 3 issues fixed"

Real-time status, not just a spinner.

### 4. Context Panel (Cursor, Copilot)

Shows what the agent can see:
- Open files
- Relevant symbols
- Active rules
- Memory items
- MCP tools available

### 5. Keyboard-First (Claude Code, all terminals)

Everything accessible via keyboard:
- `Ctrl+K` → Command palette
- `Ctrl+L` → New chat
- `Ctrl+Shift+R` → Review code
- `Ctrl+Enter` → Send with full context

---

## Beep.AI.Code Layout

```
┌──────────────┬───────────────────────────────┬──────────────────┐
│              │                               │                  │
│   AGENTS     │         CHAT CANVAS           │    CONTEXT       │
│              │                               │                  │
│ ┌──────────┐ │ ┌───────────────────────────┐ │ ┌──────────────┐ │
│ │ 🧠 React │ │ │                           │ │ │ 📁 Project   │ │
│ │   Dev    │ │ │  You: Review auth module  │ │ │              │ │
│ │          │ │ │                           │ │ │ auth/         │ │
│ │ 🔍 Code  │ │ │  Agent: Analyzing...      │ │ │  login.ts     │ │
│ │   Review │ │ │                           │ │ │  session.ts   │ │
│ │          │ │ │  📄 auth/login.ts         │ │ │  middleware.ts│ │
│ │ 🐛 Bug   │ │ │  ⚠️ Missing rate limit    │ │ │              │ │
│ │   Finder │ │ │  ⚠️ MD5 hashing (use      │ │ │ 🧠 Context    │ │
│ │          │ │ │     bcrypt)               │ │ │  login.ts:42  │ │
│ │ ✅ Test  │ │ │  ⚠️ No session expiry     │ │ │  session.ts   │ │
│ │   Writer │ │ │                           │ │ │              │ │
│ │          │ │ │  [Apply Fix] [Show Diff]  │ │ │ 📋 Rules     │ │
│ └──────────┘ │ │                           │ │ │  clean-code   │ │
│              │ │ ┌───────────────────────┐ │ │  architecture │ │
│ ──────────── │ │ │ Type a message...  [→]│ │ │              │ │
│ 📋 Reviews   │ │ └───────────────────────┘ │ │ 🔧 Tools     │ │
│  (3 pending) │ │                           │ │  file_read    │ │
│              │ │  [@files] [@agent] [@web] │ │  file_edit    │ │
│ 🕐 History   │ │                           │ │  shell        │ │
│  Yesterday   │ └───────────────────────────┘ │  github       │ │
│  3 days ago  │                               │              │ │
│              │                               └──────────────┘ │
│ ⚙️ Settings  │                                                 │
│              │  ─────────────────────────────────────────────  │
│              │  🟢 llama-3-8b · GPU · 3.2GB VRAM · localhost  │
└──────────────┴───────────────────────────────────────────────┴──┘
```

---

## Panel Specifications

### LEFT PANEL: Agent Sidebar (260px)

```
┌──────────────────┐
│ 🏠 Home          │  ← Profile home (different per profile)
│                  │
│ AGENTS           │
│ ──────────────── │
│ 🧠 React Dev  ●  │  ← Active agent (green dot)
│ 🔍 Reviewer      │
│ 🐛 Bug Finder    │
│ ✅ Test Writer   │
│                  │
│ + New Agent      │
│                  │
│ WORK ITEMS       │
│ ──────────────── │
│ 📋 Reviews  3    │  ← Badge with count
│ 🐛 Bugs     1    │
│                  │
│ RECENT CHATS     │
│ ──────────────── │
│ 🕐 Auth review   │
│ 🕐 Fix login bug │
│ 🕐 Add tests     │
│                  │
│ ──────────────── │
│ ⚙️ Settings      │
└──────────────────┘
```

**Per-profile variations:**

| Profile | Sidebar Sections |
|---------|-----------------|
| Team Lead (Dev) | Agents, Work Items (Reviews, Bugs), Recent Chats, Project Files |
| Business Analyst | Recent Searches, Document Folders, Upload |
| Team Lead (Biz) | Assistants, Recent Documents, Upload |
| Content Creator | Content History (Images, Voice, Designs), New Generation |
| Student | Nothing (sidebar collapsed by default), expandable |
| Solo Founder | Build History, Project Files, Deploy |
| IT Admin | Services, Monitoring, Users, Config |

### CENTER: Chat Canvas

The main interaction area. Always visible, always the focus.

```
┌───────────────────────────────────────────┐
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ 👤 You                              │  │
│  │                                     │  │
│  │ Can you review the auth module for  │  │
│  │ security issues?                    │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ 🧠 React Developer                  │  │
│  │                                     │  │
│  │ I'll analyze the auth module now.   │  │
│  │                                     │  │
│  │ 🔍 Reading auth/login.ts...         │  │
│  │ 🔍 Reading auth/session.ts...       │  │
│  │ 🔍 Reading auth/middleware.ts...    │  │
│  │                                     │  │
│  │ ✅ Analysis complete. Found 4 issues│  │
│  │                                     │  │
│  │ ┌───────────────────────────────┐   │  │
│  │ │ 📄 auth/login.ts:42           │   │  │
│  │ │                               │   │  │
│  │ │ 42 │ async function login(    │   │  │
│  │ │ 43 │   username: string,     │   │  │
│  │ │ 44 │   password: string      │   │  │
│  │ │ 45 │ ): Promise<User> {      │   │  │
│  │ │    │ ⚠️ No rate limiting on  │   │  │
│  │ │    │    login endpoint       │   │  │
│  │ │    │                        │   │  │
│  │ │ Suggestion: Add rate limiting│   │  │
│  │ │ using express-rate-limit    │   │  │
│  │ │                             │   │  │
│  │ │ [Apply Fix] [Show Diff]     │   │  │
│  │ └───────────────────────────────┘   │  │
│  │                                     │  │
│  │ ┌───────────────────────────────┐   │  │
│  │ │ 📄 auth/login.ts:87           │   │  │
│  │ │ ⚠️ MD5 hashing — use bcrypt   │   │  │
│  │ │ [Apply Fix] [Show Diff]       │   │  │
│  │ └───────────────────────────────┘   │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ Type a message or @mention...    [→]│  │
│  │                                     │  │
│  │ [@files] [@agent] [@web] [@git]    │  │
│  └─────────────────────────────────────┘  │
│                                           │
└───────────────────────────────────────────┘
```

**Input bar features:**
- `@files` — mention specific files for context
- `@agent` — switch agent mid-conversation
- `@web` — enable web search for this query
- `@git` — reference a commit, PR, or branch
- Drag-and-drop files to add to context
- `Shift+Enter` for newline, `Enter` to send
- Character count (not limit, just info)

### RIGHT PANEL: Context Panel (280px, collapsible)

```
┌──────────────────┐
│ CONTEXT       ✕  │
│                  │
│ 📁 PROJECT        │
│ ──────────────── │
│ 📄 auth/login.ts  │
│ 📄 auth/session   │
│ 📄 auth/middleware│
│ 📄 auth/types.ts  │
│                  │
│ + Add files      │
│                  │
│ 🧠 AGENT AWARE    │
│ ──────────────── │
│ These files are   │
│ in current context│
│                  │
│ 📄 login.ts:42    │
│ 📄 session.ts     │
│                  │
│ 📋 ACTIVE RULES   │
│ ──────────────── │
│ ✓ clean-code      │
│ ✓ architecture    │
│                  │
│ 🔧 AVAILABLE TOOLS│
│ ──────────────── │
│ file_read         │
│ file_edit         │
│ file_write        │
│ shell             │
│ search            │
│ github_pr_read    │
│ github_commit     │
│                  │
│ 🟢 7 tools ready  │
└──────────────────┘
```

---

## Status Bar (Bottom, 28px)

```
┌──────────────────────────────────────────────────────────────────┐
│ 🟢 Ready  │  llama-3-8b  │  GPU: RTX 3060 Ti  │  3.2/8GB VRAM  │
│           │  localhost   │  ⚡ 45ms/token     │  server v1.2.3  │
└──────────────────────────────────────────────────────────────────┘
```

- Shows model name, GPU status, latency
- Click model name → model picker
- Red dot if server unreachable
- Yellow dot if server busy
- Green dot if ready

---

## Command Palette (`Ctrl+K`)

```
┌──────────────────────────────────────────┐
│  🔍  Type a command...                   │
│                                          │
│  ── AGENTS ─────────────────────────────│
│  🧠  Switch to React Developer           │
│  🔍  Switch to Code Reviewer             │
│  🐛  Switch to Bug Finder                │
│  ✅  Switch to Test Writer               │
│                                          │
│  ── ACTIONS ────────────────────────────│
│  📋  Review current file                 │
│  🐛  Find bugs in current file           │
│  ✅  Write tests for current file        │
│  🔍  Search codebase...                  │
│  📄  Explain this code                   │
│                                          │
│  ── VIEW ───────────────────────────────│
│  🗂   Toggle sidebar                     │
│  📋  Toggle context panel                │
│  🌙  Toggle dark/light mode              │
│                                          │
│  ── SESSION ────────────────────────────│
│  📁  Open project folder                 │
│  📊  Session history                     │
│  ⚙️  Settings                            │
└──────────────────────────────────────────┘
```

---

## Profile-Specific UI Variations

### Team Lead (Dev) — Full Agent IDE

See layout above. All panels, code-focused, dark theme.

### Business Analyst — Document Search

```
┌──────────────────────────────────────────────────┐
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  🔍  Search your documents...           [→] │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  📂 1,247 documents indexed  │  🟢 Ready         │
│                                                  │
│  RECENT ANSWERS                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 📄 "Lease termination clause"             │  │
│  │    Section 4.2 of Office_Lease_2025.pdf   │  │
│  │    "The lease shall expire on..."         │  │
│  │                                   2h ago   │  │
│  └────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────┐  │
│  │ 📊 "Q2 revenue by region"                 │  │
│  │    From Q2_Financials.xlsx                │  │
│  │    → Chart generated              1d ago   │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  [⬆️ Upload Documents]  [📂 Browse All]          │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Content Creator — Content Studio

```
┌──────────────────────────────────────────────────┐
│  [🖼️ Images]  [🎙️ Voice]  [🎨 Design]            │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │                                            │  │
│  │  Prompt: A modern SaaS dashboard with...   │  │
│  │                                   [Generate]│  │
│  │                                            │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐    │  │
│  │  │  Gen 1  │  │  Gen 2  │  │  Gen 3  │    │  │
│  │  │         │  │         │  │         │    │  │
│  │  │ [IMG]   │  │ [IMG]   │  │ [IMG]   │    │  │
│  │  │         │  │         │  │         │    │  │
│  │  │ ⬇️ PNG  │  │ ⬇️ PNG  │  │ ⬇️ PNG  │    │  │
│  │  └─────────┘  └─────────┘  └─────────┘    │  │
│  │                                            │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Keyboard Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+K` | Command palette | Global |
| `Ctrl+L` | New chat | Chat |
| `Ctrl+Shift+R` | Review current file | Dev |
| `Ctrl+Shift+B` | Find bugs in current file | Dev |
| `Ctrl+Shift+T` | Write tests for current file | Dev |
| `Ctrl+Enter` | Send with full project context | Chat |
| `Ctrl+B` | Toggle left sidebar | Global |
| `Ctrl+J` | Toggle context panel | Global |
| `Ctrl+Shift+F` | Search codebase | Dev |
| `Ctrl+P` | Quick file open | Dev |
| `Ctrl+,` | Settings | Global |
| `Escape` | Cancel current agent action | Chat |

---

## What We Reuse From Existing Code

| Existing Component | From | Reuse As |
|-------------------|------|----------|
| `Chat.razor` | `Beep.AI.Clients.WebUI` | Main chat canvas (center panel) |
| `beep/api/client.py` | `Beep.AI.Code` | HTTP transport to Server |
| `beep/agent/loop.py` | `Beep.AI.Code` | Local agent orchestration |
| `beep/chat/prompts.py` | `Beep.AI.Code` | System prompts per agent |
| `beep/chat/stream_renderer.py` | `Beep.AI.Code` | Streaming response renderer |
| `beep/sessions/` | `Beep.AI.Code` | Conversation persistence |
| `beep/config.py` | `Beep.AI.Code` | Profile/settings storage |
| `MaterialDesignThemes` | `Beep.AI.Clients.WPF` | WPF theming |
| `simple_service_factory.py` | `Beep.AI.Server` | Profile-driven service creation |
| `hardware_advisor.py` | `Beep.AI.Server` | Hardware detection + model picking |

## What's New

| Component | Purpose |
|-----------|---------|
| WPF Shell (`Beep.AI.Code.UI.Wpf`) | Native window, tray, notifications, WebView2 host |
| Blazor Chat UI (`Beep.AI.Code.UI.Chat`) | Refactored from existing Chat.razor, profile-aware |
| Profile Manager (`beep/profiles/`) | Load/save/switch profiles, theme application |
| Agent Panel UI | Sidebar with agent switching, work items |
| Context Panel UI | Right panel with files, rules, tools |
| Command Palette | `Ctrl+K` searchable command list |
| Setup Wizard UI | Blazor-based, profile-driven onboarding |
