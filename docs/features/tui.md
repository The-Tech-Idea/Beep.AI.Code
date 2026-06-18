# TUI (Textual)

**Status:** Partial  
**Package:** `beep/tui/`

## Purpose

Full-screen terminal UI alternative to the line-oriented REPL.

## Code locations

| Module | Role |
|--------|------|
| `tui/app.py` | Main application |
| `tui/screens/chat.py` | Chat screen |
| `tui/dialogs/*` | Model selector, permissions, sessions |
| `tui/widgets/*` | Sidebar, etc. |
| `commands/tui.py` | Launcher |

## User surfaces

- `beep tui` (`--model`, `--mode`)

## Current behavior

- Chat streaming path with empty-output guard (Phase 6)
- Graceful entry/exit error handling

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| TUI-1 | Feature parity checklist vs REPL slash commands | P1 | Matrix doc |
| TUI-2 | Mouse support for file tree sidebar | P2 | Manual |
| TUI-3 | Split pane: chat + tool log | P2 | UI test |
| TUI-4 | Coding approval modal | P1 | Integration |
| TUI-5 | Windows terminal compatibility notes | P2 | Docs |
