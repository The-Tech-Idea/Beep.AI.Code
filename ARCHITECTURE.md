# Beep.AI.Code Architecture

Beep.AI.Code is a token-authenticated CLI client for Beep.AI.Server. It should stay organized around clear runtime boundaries rather than command-specific duplication.

## Runtime Layers

- `beep/cli.py`
  - Typer command registration only.
  - Delegates default invocation parsing to `beep/cli_defaults.py`.
  - Delegates command behavior to `beep/commands/*`.

- `beep/commands/*`
  - Top-level CLI commands such as `chat`, `ask`, `agent`, `review`, `test`, and `workspace`.
  - These modules should parse command options, load configuration, create clients, and call domain services.

- `beep/api/*`
  - External Beep.AI.Server transport.
  - `client.py` owns HTTP lifecycle and endpoint methods.
  - `payloads.py` owns request payload shaping.
  - `streaming.py` owns SSE response parsing.

- `beep/coding/*`
  - Beep.AI.Server Coding Assistant integration helpers.
  - Owns coding metadata envelopes, workspace prompt context, and response metadata parsing.

- `beep/chat/*`
  - Interactive REPL runtime.
  - `repl.py` owns the REPL session state and command dispatch.
  - `runner.py` owns the chat entrypoint.
  - `coding_bridge.py` owns server bootstrap for chat sessions.
  - `command_registry.py` owns slash-command registration.

- `beep/chat/commands/*`
  - Slash-command implementations grouped by business concern.
  - `llm_turns.py` owns repeated model-turn bookkeeping for chat commands: request count, coding metadata, token usage, last output, coding IDs, and approvals.
  - Individual command modules should focus on command-specific input preparation and presentation.

- `beep/agent/*`
  - Autonomous agent orchestration and tool execution.
  - Tools live under `beep/agent/tools/*`.
  - `agent/tools/factory.py` owns tool composition for local, plugin, and MCP tools.

- `beep/workspace/*`, `beep/sessions/*`, `beep/plugins/*`, `beep/rules/*`, `beep/skills/*`
  - Domain support services for workspace IO, local session persistence, plugin loading, rule loading, and skill loading.

- `beep/runtime/*`
  - Shared app-runtime composition.
  - `runtime/workspace.py` owns the per-workspace runtime cache for memory, commands, plugins, rules, and skills.

## Shared Runtime And Session Ownership

- `WorkspaceRuntime` is the shared per-workspace singleton-style object. It is cached by workspace path and plugin-enabled mode because those dependencies are expensive and mostly read-only during a CLI run.
- `ChatSession` is not a singleton. It owns mutable conversation state, local session ID, token counts, pending edits, and coding-session linkage.
- `AgentSession` is not a singleton. It owns one autonomous run loop, message history, approval mode, and tool-call counters.
- `BeepAPIClient` is not a process-wide singleton. It owns an async HTTP client lifecycle and should be closed by the command that creates it.
- Tests that need fresh workspace discovery can call `clear_workspace_runtime_cache()`.

## Multi-Agent Status

The current app supports one autonomous `AgentSession` per `/agent` or `beep agent` run. It does not yet implement coordinated multi-agent planning, sub-agent delegation, shared blackboard state, or concurrent agent workers. The architecture now has the right lower-level pieces for that future work: isolated `AgentSession` instances, shared immutable workspace runtime, and centralized tool composition.

## Clean Code Rules

- Keep one primary responsibility per file.
- Keep Python and HTML files under 500 lines.
- Put shared behavior in the owning domain module instead of repeating it in command handlers.
- Keep transport shaping in `beep/api/*`, not command modules.
- Keep Coding Assistant metadata and prompt behavior in `beep/coding/*`.
- Keep slash-command model response bookkeeping in `beep/chat/commands/llm_turns.py`.
- Keep shared initialization in `beep/runtime/*`; do not reload memory/plugins/rules/skills independently from commands.
- Avoid compatibility wrappers unless they preserve a real external contract.
