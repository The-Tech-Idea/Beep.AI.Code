# Beep.AI.Code

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Terminal-native coding assistant** that talks to **[Beep.AI.Server](https://github.com/The-Tech-Idea/Beep.AI.Server)** the same way **OpenAI Codex CLI** talks to OpenAI’s API or **Claude Code** talks to Anthropic: you authenticate with an **application API token**, stream completions, and optionally attach **Coding Assistant** workspace metadata so the server can run the same tools, sessions, and policies as the web assistant.

This package is the **official CLI companion** for Beep.AI.Server’s coding assistant—not a standalone LLM client. You run **your** server; the CLI does not ship models.

---

## Contents

- [How it compares](#how-it-compares)
- [Features at a glance](#features-at-a-glance)
- [Requirements](#requirements)
- [Install](#install)
- [Upgrade](#upgrade)
- [Self-update](#self-update)
- [Deprecations](#deprecations-and-breaking-changes)
- [First-time setup](#first-time-setup)
- [Daily usage](#daily-usage)
- [Architecture](#architecture)
- [Project memory](#project-memory)
- [Hooks](#hooks)
- [Documentation in this repo](#documentation-in-this-repo)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Security notes](#security-notes)
- [License](#license)
- [Roadmap](#roadmap)
- [Release readiness](#release-readiness-checklist)
- [Related](#related)

---

## How it compares

| Capability | Codex-style CLI | Claude Code–style | Beep.AI.Code |
|------------|-----------------|-------------------|--------------|
| Interactive REPL | ✓ | ✓ | ✓ (`beep` / `beep chat`) |
| One-shot prompt | ✓ | ✓ | ✓ (`beep "…"` / `beep ask "…"`) |
| Token auth to your backend | OpenAI | Anthropic | **Bearer → Beep.AI.Server** |
| Project/workspace binding | Project / cwd | cwd + config | **Workspace root → bootstrap → `project_id` / `session_id`** |
| Local file tools + agent loop | Varies | Varies | ✓ (`beep agent`, in-chat `/agent`) |
| RAG from your server | Usually separate | Optional | ✓ (`beep rag`, `/rag`) |
| Self-hosted / private stack | ✗ | ✗ | **✓ (your Beep.AI.Server)** |

---

## Features at a glance

- **Interactive chat** — Default `beep` / `beep chat`: streaming replies, slash commands, `@file` mentions, pinned context, git-aware hints; **Coding Assistant** bootstrap when the server accepts your token and workspace.
- **One-shot** — `beep "…"` or `beep ask "…"` for non-interactive prompts.
- **Agent loop** — `beep agent` with local tools (read / search / edit / shell), step limits, and optional **`-y`** auto-approve (use only in trusted environments).
- **Plugins** — Optional workspace and user plugins; use **`--no-plugins`** when the tree is untrusted.
- **Workspace helpers** — `tree`, `cat`, `grep`, `edit` for scripts and automation.
- **Quality** — `test`, `lint`, `review`, `analyze`, `diagnostics`, `status`.
- **Templates, sessions, RAG** — List/generate templates, manage sessions, query RAG collections (server capabilities and token scopes permitting).
- **TUI** — `beep tui` for a full terminal UI.
- **Watcher** — `beep watch` to run commands on file changes.
- **Shell completions** — `beep --install-completion` or the Bash script under `completions/`.

---

## Requirements

- **Python** 3.11+
- A running **Beep.AI.Server** instance you can reach over HTTP(S)
- An **application API token** with at least:
  - `llm:read`, `llm:write` — chat and models
  - `agent:read`, `agent:execute` — coding assistant bootstrap and agent flows (as configured on your server)
  - `rag:read` — optional, for `beep rag` / `/rag`

Create tokens from the server’s IAM / Applications area (see your server docs).

---

## Install

The console entry point is **`beep`** (see [`pyproject.toml`](pyproject.toml), package name **`beep-ai-code`**).

For end users, the recommended isolated install path today is **`pipx`**.

### Supported Python and environment assumptions

- **Required runtime:** CPython **3.11+** (`requires-python = ">=3.11"`).
- **First-class validated versions:** CPython **3.11** and **3.12**. These are the versions exercised in the current CI workflow.
- **Not supported:** Python 3.10 and earlier.
- **Newer Python releases:** may work, but are not a first-class support target until they are added to CI.
- **Environment model:** end users should prefer an isolated install via `pipx`; contributors should work from a checkout in a virtual environment with `pip install -e ".[dev]"`.
- **Managed autonomous-agent runtime:** the CLI creates and repairs its own separate environment under `~/.beepai/agents_env`; do not manually install LangGraph agent packages into the main CLI environment just to satisfy `beep agent`.

### Install channel support matrix

| Install path | Audience | Support level | Validation status |
|--------------|----------|---------------|-------------------|
| `pipx install <artifact-or-source>` | End users | **Primary recommended path** | `pipx` smoke is covered in CI against built artifacts |
| `pip install -e ".[dev]"` | Contributors | **Supported contributor path** | Used in CI test and lint jobs |
| `pip install dist/*.whl` | Early adopters / release verification | **Supported artifact path** | Fresh-venv wheel smoke is covered in CI |
| `pip install dist/*.tar.gz` | Packaging fallback | **Build artifact only, not primary user guidance** | sdist is built and checked, but not yet install-smoked in CI |
| `pipx install "git+...#subdirectory=Beep.AI.Code"` | Early adopters without a local clone | **Supported convenience path** | Documented, but not exercised in CI on every change |

Treat the wheel and `pipx` artifact flows as the canonical release-quality install surfaces. Editable installs are for local development, not for end-user support.

### From this repository (standalone clone)

If you cloned **[The-Tech-Idea/Beep.AI.Code](https://github.com/The-Tech-Idea/Beep.AI.Code)** and your shell is at the **repository root** (where `pyproject.toml` lives):

```bash
pip install -e ".[dev]"   # dev: pytest, ruff, mypy
```

Local isolated install without keeping the checkout importable on your shell path:

```bash
pipx install .
```

### From the Beep.AI.Server monorepo

If this package lives under **`Beep.AI.Server/Beep.AI.Code`**:

```bash
cd Beep.AI.Code
pip install -e ".[dev]"
# or
pipx install .
```

### pipx from Git (no local clone)

Install the package as published inside the server repo:

```bash
pipx install "git+https://github.com/The-Tech-Idea/Beep.AI.Server.git#subdirectory=Beep.AI.Code"
```

### From a built release artifact

If you already built artifacts locally with `python -m build`, the release-quality install surfaces are:

```bash
pip install dist/*.whl
# or
pipx install dist/*.whl
```

---

## Upgrade

Upgrade the main CLI using the same installation path you used originally.

## Self-update

The preferred in-product upgrade entrypoint is:

```bash
beep self-update
```

By default this is a **dry run**. It inspects the installed package metadata, detects the current install channel, and prints the update steps it would run.

Execute the detected upgrade steps with:

```bash
beep self-update --yes
```

Supported automatic channels today:

- `pipx` installs use `pipx upgrade beep-ai-code`
- package-index installs use `python -m pip install --upgrade beep-ai-code`
- VCS installs reuse the recorded VCS source
- editable or local checkout installs reuse the recorded source directory and, when applicable, run `git pull --ff-only` before reinstalling

Known limitation:

- installs from a local wheel or sdist path do **not** auto-upgrade, because the CLI cannot guess the path to a newer artifact; in that case `beep self-update` prints the manual reinstall guidance instead

If you prefer the explicit manual path, the commands below remain supported.

### Editable install from a checkout

```bash
git pull
pip install -e ".[dev]"
```

### `pipx` install from a local checkout

```bash
git pull
pipx uninstall beep-ai-code
pipx install .
```

### `pipx` install from Git

```bash
pipx uninstall beep-ai-code
pipx install "git+https://github.com/The-Tech-Idea/Beep.AI.Server.git#subdirectory=Beep.AI.Code"
```

After any CLI upgrade, run the built-in doctor surface first. It summarizes config schema state, managed-runtime compatibility, and local session-state migration status, then prints the recommended repair commands for anything that needs attention:

```bash
beep doctor
# `beep diagnostics` shows the same repair surface
```

For supported managed-runtime repair paths, the doctor surface can also apply the recommended fix directly:

```bash
beep doctor --fix
```

Today this automatic repair path is intentionally narrow: it only applies the supported managed-runtime refresh or rebuild flow when the doctor output recommends `beep agent setup` or `beep agent reinstall runtime`. Config corruption, unsupported schema versions, and local-artifact upgrade paths remain guidance-only and still require the explicit manual workflow.

If the doctor output shows a managed-runtime repair path, apply it next:

```bash
beep agent status
beep agent setup
# when status recommends a full rebuild:
beep agent reinstall runtime
```

Your main CLI config at **`~/.beepai/code.json`** is schema-versioned and legacy config payloads are migrated automatically when the CLI loads them, so normal package upgrades should not require manual config rewrites.
Local session state now follows the same rule: chat history files under **`~/.beepai/history/*.jsonl`** carry a schema marker and legacy files are upgraded in place when they are loaded, listed, or searched, and workspace **`.beep/session_memory.json`** now persists a schema version and rewrites legacy dict payloads on load.
If a previous managed-runtime setup was interrupted or left `~/.beepai/agents_env` only partially installed, `beep agent setup` now fails fast with rebuild guidance instead of layering packages onto an indeterminate runtime. In that case, use **`beep agent reinstall runtime`**.

## Deprecations And Breaking Changes

The release contract for `beep-ai-code` is:

- **Breaking changes must be called out explicitly in release notes** before or at the release that introduces them. Do not rely on users inferring them from diff volume or generic upgrade text.
- **Operator-impacting changes must include the repair path** in the release notes when they affect config schema, local session state, managed runtime compatibility, required Python versions, install commands, or token/config assumptions.
- **Deprecations should be announced before removal when practical.** The preferred path is: announce the deprecated surface, document the replacement command or workflow, keep the old path working for at least one subsequent tagged release when feasible, then remove it in a later release with an explicit breaking-change note.
- **If advance deprecation is not practical**, the release notes must say that the change is immediate and why, plus the command or migration step needed to recover.
- **Upgrade verification is part of the communication contract.** Release notes for packaging or runtime changes should tell users to run `beep doctor` after upgrading and should mention `beep agent setup` or `beep agent reinstall runtime` when those commands are the expected recovery paths.
- **README install and upgrade guidance is canonical user documentation.** If a release changes supported install channels, Python support, or repair workflows, update this README in the same change set as the code and CI validation.

---

## First-time setup

```bash
beep setup
```

You will be prompted for:

1. **Server URL** (e.g. `http://localhost:5000`)
2. **API token**
3. Optional **default model**

**Configuration** is stored at **`~/.beepai/code.json`** (file mode `0600`). The file carries a persisted schema version, and older config shapes are migrated automatically on load. You can also supply secrets via environment variables (below) instead of—or overriding—file fields, or run **`beep config-set <key> <value>`** to update keys from the shell.
Local chat sessions and workspace session-memory files are also migration-aware, so upgrading the CLI no longer requires manually rewriting legacy session JSON payloads.

### Environment overrides

| Variable | Purpose |
|----------|---------|
| `BEEP_SERVER_URL` | Base URL of Beep.AI.Server |
| `BEEP_API_TOKEN` | Application token |
| `BEEP_DEFAULT_MODEL` | Default model id |
| `BEEP_PROJECT_ID` | Existing Coding Assistant project id to bind requests to |
| `BEEP_MCP` | Enable MCP bridge (`1`, `true`, `yes`, `on`) |

Optional fields in `code.json` include **`project_id`** if you want to bind to an existing Coding Assistant project instead of relying on workspace bootstrap alone.

---

## Daily usage

### Interactive chat (default)

```bash
beep
# same as:
beep chat
```

Run without loading local plugins (safer for untrusted repos):

```bash
beep chat --no-plugins
```

Starts the **slash-command REPL**: stream responses, `@file` mentions, pinned context, git-aware hints, and server-side **Coding Assistant** integration when bootstrap succeeds.

### One-shot question

```bash
beep "How does authentication flow through the middleware?"
beep ask "Summarize beep/api/client.py"
```

### Autonomous agent (local tools + server LLM)

```bash
beep agent "Add type hints to beep/config.py" --max-steps 15
beep agent "Run tests and fix failures" -y   # auto-approve risky tools
```

Request structured output from compatible providers:

```bash
beep agent "Extract the failing test names" --response-json
beep agent "Return a typed bug report" --response-schema schemas/bug-report.json
```

Attach text files or images to the first user turn:

```bash
beep agent "Review this design brief" --input-file notes/design-brief.md
beep agent "Inspect this screenshot" --input-image screenshots/failing-test.png
beep agent "Compare these artifacts" --input-file notes/spec.txt --input-image screenshots/ui.png
```

Export the active autonomous-agent configuration as a portable bundle, then import it into the local bundle library:

```bash
beep agent export code-reviewer --output code-reviewer.beep-agent.json --name "Code Reviewer"
beep agent import code-reviewer.beep-agent.json
beep agent run code-reviewer "Review the touched files and summarize the risks"
```

Package or deploy the same portable bundle through the Phase 18 channel adapters:

```bash
beep agent package code-reviewer --output agent-artifacts
beep agent package code-reviewer --channel npm --channel python --channel github-release --channel container --dry-run
beep agent deploy code-reviewer --dry-run
beep agent deploy code-reviewer
```

Imported bundles are validated against the current CLI compatibility policy before installation and are normalized into the local bundle library under `~/.beepai/agent-bundles/`. Export preserves the active provider key, base URL, selected provider options, MCP server references, and provenance metadata without embedding API keys.

Running an imported bundle reuses the same local agent runtime, validates that the bundle supports the `local` runner target, and fails clearly if the current machine is missing any MCP servers referenced by the bundle.

The package adapters treat npm as one supported distribution channel among several, not as the canonical runtime model. Each generated channel wrapper now includes a `release-metadata.json` artifact with the same bundle version, release tag, compatibility envelope, and provenance summary that `beep agent deploy --dry-run` surfaces before contacting Beep.AI.Server.

Disable local plugins while running an agent:

```bash
beep agent "Audit dependency updates" --no-plugins
```

The agent uses **local** tools (read/search/edit/shell) and sends **`coding_assistant`** metadata on chat completions when a server session is available—aligning with Beep.AI.Server’s coding pipeline.

### MCP presets and verified tool contracts

List the built-in MCP presets and create a managed server definition for one of them:

```bash
beep mcp presets
beep mcp init playwright --preset playwright
beep mcp init remote-tools --url https://example.test/mcp --header Authorization="Bearer <token>"
```

Launch-only presets keep their `tools` list empty until you verify a real MCP tool listing. You can import a captured JSON payload from a server inspector or ask Beep to run `tools/list` directly against either a managed stdio server or a streamable HTTP endpoint:

```bash
beep mcp verify-tools playwright --from-file playwright-tools.json
beep mcp verify-tools playwright --discover
beep mcp verify-tools remote-tools --discover
```

The CLI validates the tool payload, rejects duplicates, preserves MCP `readOnlyHint` annotations as `read_only_safe`, and only updates managed definitions under `.beep/mcp/` or `~/.beepai/mcp/`. `beep mcp list` now shows both the transport and its target so stdio and HTTP definitions are easy to audit after initialization.

### Provider setup and capabilities

Use the provider admin commands to see exactly what the autonomous agent can do with the currently selected backend:

```bash
beep agent providers
beep agent status
beep agent configure openai
beep agent configure anthropic
beep agent configure openrouter
```

`beep agent status` renders the active provider, capability flags, and any surfaced provider-specific controls. Today that includes OpenAI-style **Reasoning Effort**, OpenAI-style **Parallel Tool Calls**, and Anthropic **Thinking Budget** when those settings are configured.

The Phase 16 provider audit did not find any other config-backed provider-specific controls in Beep.AI.Code beyond those surfaced settings. Additional vendor knobs will be added only with explicit config and backend-contract changes instead of implicit pass-through.

| Provider | Default base URL | Structured output | Vision | Notes |
|----------|------------------|-------------------|--------|-------|
| Beep.AI.Server | your configured server URL | Yes | Yes | Canonical hosted path for Beep coding-assistant sessions and `coding_assistant` metadata |
| OpenAI | `https://api.openai.com` | Yes | Yes | First-class hosted provider with reasoning-effort and parallel-tool-call controls |
| Anthropic | `https://api.anthropic.com` | No | Yes | Dedicated Messages API backend with surfaced thinking-budget control |
| OpenRouter | `https://openrouter.ai/api` | Yes | Yes | OpenAI-compatible transport with path-prefixed `/api` default and routed model IDs |
| LM Studio | `http://localhost:1234` | Yes | Yes | Local OpenAI-compatible runtime |
| Ollama | `http://localhost:11434/v1` | Yes | Yes | Local OpenAI-compatible runtime |

For vendors that are still moving, such as Zen-style gateways, prefer a plugin provider first. The plugin authoring path is documented in [README.md](README.md#provider-plugins), and the CLI will surface those plugins through the same `beep agent providers`, `beep agent configure`, and `beep agent status` commands.

### Programmatic agent runs

The public Python agent entrypoint now accepts provider-structured output hints and richer first-turn user content:

```python
from beep.agent.loop import run_agent


result = await run_agent(
  client,
  "Extract the failing test names from this screenshot.",
  response_format={"type": "json_object"},
  initial_user_content=[
    {"type": "text", "text": "Return only the failing test identifiers."},
    {
      "type": "image_url",
      "image_url": {"url": "data:image/png;base64,..."},
    },
  ],
)
```

`initial_user_content` is appended to the first user turn while the runtime keeps the normal goal-oriented agent instructions. `resume_agent(..., response_format=...)` can continue a structured-output run on an existing checkpointed thread; multimodal input belongs on the initial run because the thread already persists prior messages.

### Managed agent runtime lifecycle

The autonomous agent uses a separate managed Python environment under **`~/.beepai/agents_env`** for LangGraph and workspace-intelligence packages.

Check its state and the recommended repair command:

```bash
beep agent status
```

Create or refresh the managed runtime when it is missing, incomplete, or normally stale:

```bash
beep agent setup
```

Rebuild the managed runtime from scratch when status recommends a full rebuild, especially after compatibility-metadata changes:

```bash
beep agent reinstall runtime
```

Repair one package inside the managed runtime without rebuilding everything:

```bash
beep agent reinstall jedi
beep agent reinstall semble
```

### Full TUI

```bash
beep tui
```

### Workspace utilities (scripting)

```bash
beep tree . --depth 4
beep cat path/to/file.py --start 1 --end 80
beep grep "TODO" src/
beep edit path/to/file.py --content "..." --yes
```

### Quality and diagnostics

```bash
beep test
beep lint --fix
beep review --staged
beep analyze .
beep diagnostics
beep status
```

### Templates, sessions, RAG

```bash
beep template list
beep template generate <name> <output_path>
beep sessions list
beep sessions export <id>
beep sessions delete <id>
beep rag query "deployment checklist"
beep rag collections
```

### File watcher

```bash
beep watch --pattern "*.py" --command "beep lint"
```

### Shell completions

Typer can install shell completion scripts directly:

```bash
beep --install-completion
```

Manual Bash setup (from **this repository’s root**):

```bash
source completions/beep.bash
```

If your checkout path differs, use the absolute path to `completions/beep.bash` (for example when appending to `~/.bashrc` on Linux or macOS).

---

## Architecture

```text
┌─────────────────┐     Bearer token      ┌──────────────────────┐
│  Beep.AI.Code   │ ───────────────────► │   Beep.AI.Server     │
│  (this CLI)     │   /v1/chat/completions│  OpenAI-compatible  │
│                 │   + coding_assistant  │  + Coding Assistant   │
│  Typer + Rich   │   /ai-middleware/...  │  + RAG / IAM          │
│  httpx async    │   bootstrap           │                       │
└────────┬────────┘                       └──────────────────────┘
         │
         ▼
   Local workspace (cwd → git root)
   .beep.md / .beep/  project memory
```

**Primary HTTP surface** (see [`beep/api/client.py`](beep/api/client.py)):

| Area | Endpoints (representative) |
|------|----------------------------|
| Health | `GET /api/health` |
| Models / chat | `GET /v1/models`, `GET /v1/models/{id}`, `POST /v1/chat/completions` (streaming supported) |
| Other LLM surfaces | `POST /v1/messages`, `POST /v1/responses`, `POST /v1/embeddings` (when enabled on the server) |
| Coding Assistant | `POST /ai-middleware/api/coding-assistant/workspaces/bootstrap`, project bootstrap/sessions under `/ai-middleware/api/coding-assistant/projects/...`, `POST .../sessions/compact` |
| RAG | `POST /v1/rag/query`, `GET /v1/rag/collections` |
| Diagnostics | `GET /ai-middleware/api/tokens/check` |

Session-auth **web** routes under `/coding-assistant/*` are **not** used by this CLI; keep automation on token-authenticated APIs.

---

## Project memory

Same idea as a project-level `CLAUDE.md`: instructions loaded from the **workspace root** (auto-detected):

| Path | Role |
|------|------|
| `.beep.md` | Global instructions for the model |
| `.beep/habits.md` | Bullet habits / preferences |
| `.beep/commands.md` | Custom command descriptions (`- name: description`) |
| `.beep/ignore` | Extra ignore patterns for context |

Loaded in `beep/memory/loader.py` and merged into the system prompt in the REPL.

---

## Hooks

User-level hook definitions live in **`~/.beepai/hooks.json`** (`beep/hooks/manager.py`). Use these to run shell snippets around events (see `/hooks` in chat for workflow integration).

---

## Documentation in this repo

| Document | Purpose |
|----------|---------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Runtime layers, workspace cache vs sessions, boundaries for contributors |
| [`MASTER-TODO-TRACKER.md`](MASTER-TODO-TRACKER.md) | Roadmap phases, checklists, verification |
| [`docs/INDEX.md`](docs/INDEX.md) | Top-level engineering doc index |
| [`docs/ENGINEERING_IMPLEMENTATION_GUIDELINES.md`](docs/ENGINEERING_IMPLEMENTATION_GUIDELINES.md) | Implementation standards |
| [`AGENTS.md`](AGENTS.md) | Agent frameworks and service-design rules shared with the Beep.AI.Server ecosystem |

---

## Troubleshooting

- **Cannot connect** — Check `BEEP_SERVER_URL` (scheme, host, port), TLS/proxy, and that Beep.AI.Server is running. Run `beep diagnostics`.
- **401 / 403** — Token missing, expired, or missing scopes (`llm:*`, `agent:*`, `rag:*` as needed). Confirm IAM on the server.
- **Bootstrap / workspace issues** — Ensure the process cwd or intended **workspace root** is correct; set **`BEEP_PROJECT_ID`** or `project_id` in `code.json` if you must bind an existing project. `beep status` and `beep diagnostics` summarize client config and reachability.
- **Unsure how this install should be upgraded** — Run `beep self-update` first. It prints the detected install channel and the exact steps the CLI can run for that installation.
- **Doctor found a supported managed-runtime repair and you want the CLI to apply it** — Run `beep doctor --fix`. It only auto-runs the supported managed-runtime refresh or rebuild flow.
- **Autonomous agent says the managed runtime is not ready** — Run `beep agent status` first. If the repair command is `beep agent setup`, that means the managed runtime is missing, incomplete, or needs a normal refresh.
- **Autonomous agent says the managed runtime needs a rebuild** — Run `beep agent reinstall runtime`. This is the full repair path when compatibility metadata changed and a refresh is not enough.
- **One managed runtime package is broken** — Reinstall just that package with `beep agent reinstall <package>`, for example `beep agent reinstall jedi`.
- **Untrusted repositories** — Use **`beep chat --no-plugins`** and **`beep agent ... --no-plugins`** so local plugin code is not loaded.

---

## Development

```bash
pip install -e ".[dev]"
pytest -v
ruff check beep tests
mypy beep
```

Larger changes should follow the layering described in [`ARCHITECTURE.md`](ARCHITECTURE.md).

### CI workflow

The repo now ships a real GitHub Actions workflow at [`.github/workflows/beep-ai-code-ci.yml`](.github/workflows/beep-ai-code-ci.yml).

It currently validates:

- focused agent-runtime pytest coverage on Python 3.11 and 3.12
- `ruff check beep tests`
- wheel and sdist builds
- `twine check dist/*`
- fresh-venv wheel install smoke
- `pipx` install smoke
- synthetic older-to-current wheel upgrade smoke

If this package is hosted as a subdirectory inside the Beep.AI.Server monorepo, keep the same workflow logic but scope checkout paths and working-directory settings to `Beep.AI.Code/`.

### Layout

| Path | Responsibility |
|------|------------------|
| `beep/cli.py` | Typer app, default routing (`beep` vs subcommands) |
| `beep/api/client.py` | Async Beep.AI.Server client |
| `beep/chat/repl.py` | REPL, `ChatSession`, bootstrap, streaming |
| `beep/chat/commands/` | Slash commands |
| `beep/agent/` | Tool loop + approvals |
| `beep/plugins/registry.py` | Plugin types (tools / slash / context)—extension point |
| `beep/memory/` | `.beep.md` family |
| `beep/templates/` | Built-in codegen templates |
| `tests/` | pytest suite |

---

## Provider Plugins

Backend providers are plug-and-play.

- Runtime plugin discovery searches `~/.beepai/plugins/*.py` and `<workspace>/.beep/plugins/*.py`.
- Built-in providers now cover Beep.AI.Server, OpenAI, Anthropic, OpenRouter, LM Studio, and Ollama.
- For emerging or less stable vendors such as Zen, prefer a plugin-first provider instead of adding a new built-in provider immediately.

For OpenAI-compatible vendors, subclass `OpenAICompatibleProviderPluginBase` from [beep/agent/provider_plugin_base.py](beep/agent/provider_plugin_base.py). A minimal Zen-style plugin looks like this:

```python
from beep.agent.provider_plugin_base import OpenAICompatibleProviderPluginBase
from beep.plugins.registry import PluginInfo


class ZenBackendPlugin(OpenAICompatibleProviderPluginBase):
  info = PluginInfo(
    name="zen-backend-plugin",
    version="0.1.0",
    description="Zen provider plugin",
  )
  provider_key_value = "zen"
  display_name = "Zen"
  default_base_url_value = "https://your-zen-endpoint.example/api"

  def activate(self) -> None:
    pass

  def configuration_notes(self, config):
    del config
    return (
      "Set agent_api_key to your Zen API key.",
      "Set agent_model to the Zen model ID you want the coding agent to use.",
      "Override agent_base_url only when targeting a non-default Zen gateway.",
    )
```

Drop that plugin into `~/.beepai/plugins/` or `.beep/plugins/`, then run `beep agent providers` or `beep agent configure zen`.

---

## Security notes

- Treat **`~/.beepai/code.json`** like a credential store; never commit it.
- **`beep agent`** with **`-y` / `--yes`** auto-approves operations that would normally prompt (shell, writes, etc.). Use only in trusted sandboxes.
- Shell tool execution is **local**; scope tokens and server policies to least privilege.
- Use `--no-plugins` on `beep chat` / `beep agent` to disable loading untrusted local plugins.
- MCP subprocess tools are guarded with timeout and output-size limits to avoid hangs and runaway output.

---

## License

MIT — see [`pyproject.toml`](pyproject.toml) and [`LICENSE.txt`](LICENSE.txt).

---

## Roadmap

Enhancements (plugins runtime, skills, rules, templates v2, MCP, parity work) are tracked in **[MASTER-TODO-TRACKER.md](MASTER-TODO-TRACKER.md)** with phased checklists and verification criteria.

## Release Readiness Checklist

Before publishing `beep-ai-code` to PyPI:

- Expected release bundle:
  - exactly one wheel in `dist/`
  - exactly one source distribution in `dist/`
  - one `SHA256SUMS.txt` manifest generated from the built wheel and sdist via `python tools/ci/generate_release_checksums.py --artifacts-dir dist`

- Verify packaging metadata and build locally:
  - `python -m pip install --upgrade build twine`
  - `python -m build`
  - `python tools/ci/generate_release_checksums.py --artifacts-dir dist`
  - `python -m twine check dist/*.whl dist/*.tar.gz`
- Validate portable bundle package and deploy dry runs without live credentials:
  - `pytest -q tests/test_agent_package_commands.py tests/test_agent_deploy_commands.py`
  - confirm each local packaging channel emits `release-metadata.json`
  - confirm `beep agent deploy <bundle> --dry-run` prints the expected release tag before any hosted import
- Run quality gates:
  - `pytest -q`
  - `ruff check beep tests`
  - `mypy beep`
- Validate installation paths:
  - `pip install dist/*.whl` in a fresh venv
  - `pipx install dist/*.whl` smoke test
- Validate CLI ergonomics:
  - `beep --help`
  - `beep doctor`
  - `beep diagnostics`
  - `beep self-update`
  - `beep --install-completion` (or `source completions/beep.bash`)
- Validate release communication:
  - release notes explicitly call out deprecations, removals, and breaking changes
  - release notes include upgrade verification and any required repair commands (`beep doctor`, `beep agent setup`, `beep agent reinstall runtime`)
  - README install and upgrade sections match the release being published
  - release notes identify the wheel/sdist pair being published and reference the matching `SHA256SUMS.txt` manifest

---

## Related

- **[Beep.AI.Server](https://github.com/The-Tech-Idea/Beep.AI.Server)** — API server, Coding Assistant, RAG, IAM
- **[AGENTS.md](AGENTS.md)** — agent frameworks and service design rules for the server ecosystem
