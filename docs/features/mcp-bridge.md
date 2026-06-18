# MCP Bridge

**Status:** Mature (core shipped/hardened in phase 9; backlog is incremental)  
**Package:** `beep/mcp/`

## Purpose

Attach Model Context Protocol servers as agent tools (stdio/HTTP), with presets and contract verification.

## Code locations

| Module | Role |
|--------|------|
| `client.py` | MCPClient, tool mapping |
| `presets.py`, `preset_tools.py` | Built-in server presets |
| `discovery.py`, `live_discovery.py` | Tool discovery |
| `tool_contracts.py` | Static contracts |
| `http_transport.py` | Streamable HTTP MCP |
| `commands/mcp.py` | CLI |

## User surfaces

- `BEEP_MCP=1` + `mcp_servers` in `code.json`
- `beep mcp list|presets|init|verify-tools`
- REPL `/mcp` extensions

## Current behavior

- Env gate required; timeout and output truncation
- OpenAI tool schema mapping for chat/agent
- `verify-tools` for preset upgrades

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| MCP-1 | MCP server health in `beep diagnostics` | P1 | Diagnostics test |
| MCP-2 | Per-server enable/disable without editing JSON | P2 | CLI `mcp enable` |
| MCP-3 | OAuth MCP transports (when spec stable) | P3 | Spike |
| MCP-4 | Auto-restart crashed stdio servers | P2 | Integration test |
| MCP-5 | Document preset security model in user docs | P1 | Docs review |
