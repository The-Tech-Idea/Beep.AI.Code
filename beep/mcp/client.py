"""MCP client for connecting to MCP servers.

Enables the agent to use tools from external MCP servers
for extended capabilities (databases, APIs, etc.).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.config import MCPServerConfig
from beep.mcp.http_transport import close_http_mcp_session, initialize_http_mcp_session, post_http_jsonrpc_request
from beep.mcp.live_discovery import MCP_PROTOCOL_VERSION
from beep.utils.json_logging import log_event

MCP_EXEC_TIMEOUT_SECONDS = 20.0
MCP_MAX_OUTPUT_CHARS = 20000


async def _terminate_process(process: Any) -> None:
    try:
        process.kill()
    except ProcessLookupError:
        return
    except Exception:
        return

    try:
        await process.communicate()
    except Exception:
        return


@dataclass
class MCPServer:
    """Configuration for an MCP server."""

    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    connected: bool = False


@dataclass
class MCPTool:
    """A tool provided by an MCP server."""

    name: str
    description: str
    parameters: dict[str, Any]
    read_only_safe: bool
    requires_human_approval: bool
    server_name: str
    server_transport: str = "stdio"
    server_command: str | None = None
    server_args: list[str] = field(default_factory=list)
    server_env: dict[str, str] = field(default_factory=dict)
    server_url: str | None = None
    server_headers: dict[str, str] = field(default_factory=dict)


class MCPClient:
    """Client for MCP server tool integration.

    This provides the interface for discovering and using tools
    from MCP servers. Full MCP protocol implementation requires
    the mcp package.
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServer] = {}
        self._tools: list[MCPTool] = []

    def register_server(self, server: MCPServer) -> None:
        """Register an MCP server configuration."""
        self._servers[server.name] = server

    def list_servers(self) -> list[str]:
        """List registered MCP servers."""
        return list(self._servers.keys())

    def list_tools(self) -> list[MCPTool]:
        """List all available MCP tools."""
        return list(self._tools)

    def add_tool(self, tool: MCPTool) -> None:
        """Add a tool from an MCP server."""
        self._tools.append(tool)

    def to_agent_tools(self) -> list[BaseTool]:
        """Convert MCP tools to agent tool interface."""
        return [MCPToolAdapter(t) for t in self._tools]

    @classmethod
    def from_config(cls, servers: list[MCPServerConfig]) -> MCPClient:
        """Create a client from static config declarations."""
        client = cls()
        for server_cfg in servers:
            client.register_server(
                MCPServer(
                    name=server_cfg.name,
                    transport=server_cfg.transport,
                    command=server_cfg.command,
                    args=list(server_cfg.args),
                    env=dict(server_cfg.env),
                    url=server_cfg.url,
                    headers=dict(server_cfg.headers),
                    connected=False,
                )
            )
            for tool_cfg in server_cfg.tools:
                client.add_tool(
                    MCPTool(
                        name=tool_cfg.name,
                        description=tool_cfg.description or f"MCP tool from {server_cfg.name}",
                        parameters=tool_cfg.parameters or {},
                        read_only_safe=tool_cfg.read_only_safe,
                        requires_human_approval=tool_cfg.requires_human_approval,
                        server_name=server_cfg.name,
                        server_transport=server_cfg.transport,
                        server_command=server_cfg.command,
                        server_args=list(server_cfg.args),
                        server_env=dict(server_cfg.env),
                        server_url=server_cfg.url,
                        server_headers=dict(server_cfg.headers),
                    )
                )
        return client


class MCPToolAdapter(BaseTool):
    """Adapts an MCP tool to the agent tool interface."""

    def __init__(self, mcp_tool: MCPTool) -> None:
        self._tool = mcp_tool

    @property
    def name(self) -> str:
        return self._tool.name

    @property
    def description(self) -> str:
        return f"[MCP:{self._tool.server_name}] {self._tool.description}"

    @property
    def parameters(self) -> dict[str, Any]:
        return self._tool.parameters

    @property
    def read_only_safe(self) -> bool:
        """MCP tools are external and must be opted into read-only mode explicitly."""
        return self._tool.read_only_safe

    @property
    def requires_human_approval(self) -> bool:
        """Whether the MCP tool stays behind the graph approval gate."""
        return self._tool.requires_human_approval

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the MCP tool."""
        if self._tool.server_transport == "http":
            return await self._execute_http(**kwargs)

        cmd = self._tool.server_command
        args = self._tool.server_args
        env = {**os.environ, **self._tool.server_env}
        payload = {"tool": self._tool.name, "arguments": kwargs}
        log_event(
            "mcp.tool.start",
            tool_name=self._tool.name,
            server_name=self._tool.server_name,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                cmd,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except Exception as exc:
            log_event(
                "mcp.tool.error",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                error=f"start_failed: {exc}",
            )
            return ToolResult(success=False, output="", error=f"Failed to start MCP server: {exc}")

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate((json.dumps(payload) + "\n").encode("utf-8")),
                timeout=MCP_EXEC_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            await _terminate_process(process)
            log_event(
                "mcp.tool.error",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                error=f"timeout_after_{MCP_EXEC_TIMEOUT_SECONDS:.0f}s",
            )
            return ToolResult(
                success=False,
                output="",
                error=f"MCP tool {self._tool.name} timed out after {MCP_EXEC_TIMEOUT_SECONDS:.0f}s",
            )
        except asyncio.CancelledError:
            await _terminate_process(process)
            raise
        except Exception as exc:
            await _terminate_process(process)
            error_text = f"MCP transport failure: {exc}"
            log_event(
                "mcp.tool.error",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                error=f"transport_failed: {exc}",
            )
            return ToolResult(success=False, output="", error=error_text)
        stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
        stdout_truncated = False
        stderr_truncated = False
        if len(stdout_text) > MCP_MAX_OUTPUT_CHARS:
            stdout_text = stdout_text[:MCP_MAX_OUTPUT_CHARS] + "\n...[truncated]"
            stdout_truncated = True
        if len(stderr_text) > MCP_MAX_OUTPUT_CHARS:
            stderr_text = stderr_text[:MCP_MAX_OUTPUT_CHARS] + "\n...[truncated]"
            stderr_truncated = True
        if stdout_truncated or stderr_truncated:
            log_event(
                "mcp.tool.output_truncated",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
                max_chars=MCP_MAX_OUTPUT_CHARS,
            )

        if process.returncode != 0:
            error_text = stderr_text or stdout_text
            error_text = error_text or f"MCP process exited with {process.returncode}"
            log_event(
                "mcp.tool.error",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                error=error_text[:500],
                return_code=process.returncode,
            )
            return ToolResult(success=False, output="", error=error_text)

        if not stdout_text:
            log_event(
                "mcp.tool.success",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                output_chars=0,
                return_code=process.returncode,
            )
            return ToolResult(success=True, output="")

        try:
            parsed = json.loads(stdout_text)
        except json.JSONDecodeError:
            log_event(
                "mcp.tool.success",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                output_chars=len(stdout_text),
                parse_mode="raw_text",
                return_code=process.returncode,
            )
            return ToolResult(success=True, output=stdout_text)

        if isinstance(parsed, dict):
            if parsed.get("success") is False:
                error_message = str(parsed.get("error", "MCP tool execution failed"))
                log_event(
                    "mcp.tool.error",
                    tool_name=self._tool.name,
                    server_name=self._tool.server_name,
                    error=error_message[:500],
                    return_code=process.returncode,
                    parse_mode="json_dict",
                )
                return ToolResult(
                    success=False,
                    output=str(parsed.get("output", "")),
                    error=error_message,
                )
            if "output" in parsed:
                parsed_output = str(parsed["output"])
                log_event(
                    "mcp.tool.success",
                    tool_name=self._tool.name,
                    server_name=self._tool.server_name,
                    output_chars=len(parsed_output),
                    parse_mode="json_output",
                    return_code=process.returncode,
                )
                return ToolResult(success=True, output=parsed_output)

        log_event(
            "mcp.tool.success",
            tool_name=self._tool.name,
            server_name=self._tool.server_name,
            output_chars=len(stdout_text),
            parse_mode="json_fallback",
            return_code=process.returncode,
        )
        return ToolResult(success=True, output=stdout_text)

    async def _execute_http(self, **kwargs: Any) -> ToolResult:
        server_url = self._tool.server_url or ""
        session = await initialize_http_mcp_session(
            MCPServerConfig(
                name=self._tool.server_name,
                transport="http",
                url=server_url,
                headers=dict(self._tool.server_headers),
            ),
            timeout_seconds=MCP_EXEC_TIMEOUT_SECONDS,
            protocol_version=MCP_PROTOCOL_VERSION,
            client_info={"name": "Beep.AI.Code", "version": "dev"},
        )
        try:
            response = await post_http_jsonrpc_request(
                session,
                request_id=2,
                method="tools/call",
                params={"name": self._tool.name, "arguments": kwargs},
                timeout_seconds=MCP_EXEC_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            await close_http_mcp_session(session, timeout_seconds=MCP_EXEC_TIMEOUT_SECONDS)
            error_text = str(exc)
            log_event(
                "mcp.tool.error",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                error=error_text[:500],
                transport="http",
            )
            return ToolResult(success=False, output="", error=error_text)

        await close_http_mcp_session(session, timeout_seconds=MCP_EXEC_TIMEOUT_SECONDS)
        result = response.get("result")
        if not isinstance(result, dict):
            error_text = "MCP HTTP tool response must include a JSON object result"
            log_event(
                "mcp.tool.error",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                error=error_text,
                transport="http",
            )
            return ToolResult(success=False, output="", error=error_text)

        output_text = _render_http_tool_result_output(result)
        if bool(result.get("isError", False)):
            error_text = output_text or f"MCP tool {self._tool.name} reported an error"
            log_event(
                "mcp.tool.error",
                tool_name=self._tool.name,
                server_name=self._tool.server_name,
                error=error_text[:500],
                transport="http",
                parse_mode="mcp_http_result",
            )
            return ToolResult(success=False, output=output_text, error=error_text)

        log_event(
            "mcp.tool.success",
            tool_name=self._tool.name,
            server_name=self._tool.server_name,
            output_chars=len(output_text),
            transport="http",
            parse_mode="mcp_http_result",
        )
        return ToolResult(success=True, output=output_text)


def _render_http_tool_result_output(result: dict[str, Any]) -> str:
    parts: list[str] = []
    content_items = result.get("content")
    if isinstance(content_items, list):
        for item in content_items:
            if not isinstance(item, dict):
                parts.append(str(item))
                continue
            item_type = str(item.get("type") or "").strip().lower()
            if item_type == "text":
                text = str(item.get("text") or "").strip()
                if text:
                    parts.append(text)
                continue
            if item_type == "resource":
                resource = item.get("resource")
                if isinstance(resource, dict):
                    resource_text = str(resource.get("text") or "").strip()
                    if resource_text:
                        parts.append(resource_text)
                        continue
                    resource_uri = str(resource.get("uri") or "").strip()
                    if resource_uri:
                        parts.append(resource_uri)
                        continue
            parts.append(json.dumps(item, sort_keys=True))
    if not parts and "structuredContent" in result:
        return json.dumps(result["structuredContent"], sort_keys=True)
    return "\n".join(part for part in parts if part).strip()
