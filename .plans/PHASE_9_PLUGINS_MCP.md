# Phase 9 — Plugin System & MCP Bridge

**Goal:** The plugin system and MCP bridge extend the agent's toolset
beyond the built-in tools. Both must be stable, safe, and clearly bounded.

---

## Todo Tracker

### Fixes

- [x] **plugins/runtime.py — Plugin discovery walks all discovery paths even if
  one raises `PermissionError`.** A single inaccessible directory crashes the whole
  discovery pass.
  Fixed: discovery now catches `PermissionError`/`OSError` per path, logs a warning,
  and continues scanning the remaining plugin directories.

- [x] **factory.py — `build_agent_tools()` calls `get_plugin_tools()` without a
  `workspace_root` parameter.** Plugin tools that need workspace context receive
  `None` and may behave unexpectedly.
  Fixed: `build_agent_tools(...)` passes `workspace_root` through the registry and
  workspace-intelligence seams so plugin tools can bind to the active workspace.

- [x] **mcp/ — MCP bridge is optional (`BEEP_MCP=true`) but the import is unconditional
  in some code paths.** If `mcp` package is not installed, importing fails.
  Fixed: MCP client imports are guarded with `try/except ImportError`, and the factory
  logs a debug message before skipping MCP tool wiring when the package is absent.

- [x] **plugins/runtime.py — Loaded plugins are stored in a flat dict by name.**
  If two plugins have the same `name` field the second silently overwrites the first.
  Fixed: duplicate plugin names now raise `PluginNameConflictError` at registration time.

### Enhancements

- [x] **factory.py — Add `plugin_tool_schema_validation`.**
  Fixed: plugin and workspace-intelligence tools are validated at load time, invalid
  schemas are rejected before execution, and validation failures are recorded in load errors.

- [x] **mcp/ — Add `list_mcp_tools()` command.**
  Fixed: the `/mcp` command supports `tools` and `servers` views so operators can
  inspect registered MCP tools and server entries interactively.

- [x] **plugins/ + mcp/ — Auto-discover plugin and MCP definitions from files and generate them from the CLI.**
  Fixed: plugin discovery now reads extra search paths from `~/.beepai/plugins.json`
  and `<workspace>/.beep/plugins.json`, MCP server discovery now merges managed
  server files from `~/.beepai/mcp/*.json`, `<workspace>/.beep/mcp/*.json`, and
  workspace `.vscode/mcp.json`, and the CLI now ships `beep plugins paths`,
  `beep plugins add-path`, `beep mcp list`, and `beep mcp init` for managing
  those file-backed definitions.

- [x] **mcp/ — Package verified launch presets for common third-party MCP servers.**
  Fixed: the CLI now ships a verified preset catalog for Firecrawl, Glif,
  Perplexity, Playwright, and Chrome DevTools via `beep mcp presets` and
  `beep mcp init --preset ...`. These presets store only verified launch
  metadata, docs links, and required environment guidance; static tool
  declarations remain intentionally empty until they can be validated safely.

- [x] **mcp/ — Ship verified static tool contracts where vendor docs publish them explicitly.**
  Fixed: Firecrawl, Glif, and Perplexity presets now write documented `tools`
  entries with verified names, descriptions, and input fields, so discovered
  preset configs surface agent-callable MCP tools without guessing schemas.
  Playwright and Chrome DevTools remain launch-only because the reviewed docs did
  not publish a comparable stable tool schema surface.

- [x] **factory.py — Support tool category filtering.**
  Fixed: `BaseTool.category` derives stable defaults and `build_agent_tools(categories=...)`
  filters the composed tool list by category.

- [x] **plugins/ — Plugin hot-reload.**
  Fixed: development-only plugin hot-reload support is implemented behind `BEEP_DEV=1`.

## Deferred Backlog

- [x] **Verified static tool contracts for third-party MCP presets.**
  Firecrawl, Glif, and Perplexity still ship verified static tool metadata from
  reviewed vendor docs. Playwright, Chrome DevTools, and any future launch-only
  presets now stay schema-empty until an operator explicitly runs
  `beep mcp verify-tools <server> --from-file <tool-contracts.json>` with a real
  tool listing captured from the server or its inspector output, or
  `beep mcp verify-tools <server> --discover` to launch the managed stdio server
  and fetch `tools/list` live. The CLI validates the payload shape, rejects
  duplicates, preserves MCP `readOnlyHint` annotations as `read_only_safe`, and
  persists only managed `.beep/mcp/*.json` definitions so launch-only presets can
  be safely upgraded without guessing vendor schemas.
---

## Acceptance Criteria

1. Plugin discovery continues past permission-denied directories.
2. Duplicate plugin names raise a clear error at load time.
3. MCP import failures are non-fatal and logged at DEBUG.
4. `factory.py` supports category-based tool filtering.
5. Plugin tool schemas are validated at load time.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/plugins/runtime.py` | ✅ Error handling + duplicate detection |
| `beep/agent/tools/factory.py` | ✅ Schema validation + category filtering |
| `beep/mcp/` | ✅ Guarded import |
| `beep/chat/commands/` | ✅ /mcp tools command |
| `beep/mcp/tool_contracts.py` | ✅ Verified tool-contract payload validation |
