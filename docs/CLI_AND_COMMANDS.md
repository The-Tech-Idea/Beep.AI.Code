# CLI & Command Reference

Entry point: **`beep`** (`beep.cli:main`). Default invocation with no subcommand starts **interactive chat** (same as `beep chat`).

Registration source: [`beep/cli_command_registration.py`](../beep/cli_command_registration.py).

## Core commands

| Command | Description |
|---------|-------------|
| `beep` | Interactive chat REPL |
| `beep chat` | Same as default; options: `--model`, `--mode`, `--resume`, `--tokens`, `--no-plugins` |
| `beep ask <question>` | One-shot prompt |
| `beep setup` | Interactive configuration wizard |
| `beep status` | Server health and connection |
| `beep version` | Package version |
| `beep config` | Show `~/.beepai/code.json` |
| `beep config-set <key> <value>` | Update config key |
| `beep agent [goal]` | Autonomous agent (see Agent section) |

### Default one-shot

```bash
beep "Explain the auth middleware"
beep ask "Summarize beep/api/client.py"
beep --model my-model "question with flags before text"
```

## Agent command family

`beep agent` accepts extra argv for sub-operations:

| Invocation | Purpose |
|------------|---------|
| `beep agent "<goal>"` | Run LangGraph agent loop |
| `beep agent setup` | Provider / runtime setup |
| `beep agent status` | Managed runtime status |
| `beep agent providers` | List providers |
| `beep agent configure [provider]` | Provider wizard |
| `beep agent resume <thread_id>` | Resume graph thread |
| `beep agent export <agent_id>` | Export portable bundle |
| `beep agent import <bundle>` | Import bundle |
| `beep agent deploy <bundle_or_id>` | Deploy to server |
| `beep agent package <bundle_or_id>` | Package for channel |
| `beep agent run <bundle> <goal>` | Run imported bundle locally |
| `beep agent reinstall <package\|runtime>` | Reinstall managed deps |
| `beep agent uninstall [--yes]` | Remove managed runtime |

Common flags: `--max-steps`, `--yes`, `--sandbox`, `--model`, `--no-plugins`, `--response-json`, `--response-schema`, `--input-file`, `--input-image`.

## Workspace & quality

| Command | Description |
|---------|-------------|
| `beep tree [path]` | Directory tree (`--depth`, `--all`) |
| `beep cat <path>` | File view (`--start`, `--end`, `--raw`) |
| `beep grep <pattern> [path]` | Regex search |
| `beep edit <path>` | Apply edit (`--content`, `--yes`) |
| `beep review` | AI code review (`--staged`, `--file`, `--model`) |
| `beep test` | Run tests (`--file`, `--watch`, `--framework`, `--timeout`) |
| `beep lint` | Lint (`--fix`, `--linter`) |
| `beep analyze [path]` | Codebase statistics |
| `beep watch` | File watcher (`--pattern`, `--command`, `--debounce`, `--path`) |

## Operations

| Command | Description |
|---------|-------------|
| `beep tui` | Full Textual UI |
| `beep diagnostics` | Environment and plugin diagnostics |
| `beep doctor [--fix]` | Upgrade/repair guidance |
| `beep self-update [--yes]` | Update workflow for this install |

## Command groups

### `beep template`

| Subcommand | Description |
|------------|-------------|
| `list` | List templates (builtin, user, workspace) |
| `generate <name> <output>` | Generate from template |

### `beep sessions`

| Subcommand | Description |
|------------|-------------|
| `list` | Local session history |
| `export <id>` | Export (`--format markdown\|json`) |
| `delete <id>` | Delete session record |

### `beep rag`

| Subcommand | Description |
|------------|-------------|
| `query <text>` | RAG query against server |
| `collections` | List collections |

### `beep plugins`

| Subcommand | Description |
|------------|-------------|
| `paths` | Show discovery paths |
| `add-path <dir>` | Add plugin search path |

### `beep mcp`

| Subcommand | Description |
|------------|-------------|
| `list` | Configured MCP servers |
| `presets` | Built-in preset catalog |
| `init` | Scaffold MCP config |
| `verify-tools <server>` | Validate tool contracts |

## REPL slash commands (representative)

Slash commands are registered under `beep/chat/commands/`. Categories include:

| Module area | Examples |
|-------------|----------|
| `session.py` | `/clear`, `/resume`, `/sessions`, `/compact` |
| `coding.py` | `/coding on\|off`, coding approvals |
| `model.py` | `/model`, `/max_tokens` |
| `memory.py` | `/memory`, project memory reload |
| `productivity.py` | `/task`, `/watch`, git helpers |
| `extensions.py` | `/plugins`, `/skills`, `/rules`, `/mcp` |
| `system.py` | `/help`, `/status`, `/diagnostics`, templates |
| `misc.py` | `/agent`, `/rag`, `/retry`, `/summary` |

Run `/help` in chat for the authoritative list for your build.

## Environment variables

See [README.md](../README.md#environment-overrides) and [features/configuration-setup.md](features/configuration-setup.md).
