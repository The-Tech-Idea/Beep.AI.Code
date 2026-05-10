"""Live MCP tool discovery helpers for managed stdio servers."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from beep.config import MCPServerConfig, MCPToolConfig
from beep.mcp.http_transport import close_http_mcp_session, initialize_http_mcp_session, post_http_jsonrpc_request
from beep.mcp.tool_contracts import parse_verified_tool_contracts

MCP_DISCOVERY_TIMEOUT_SECONDS = 15.0
MCP_PROTOCOL_VERSION = "2024-11-05"


@dataclass(frozen=True)
class LiveMcpDiscoveryResult:
    """Validated tools plus live server provenance from MCP initialize."""

    tools: list[MCPToolConfig]
    protocol_version: str | None = None
    server_info: dict[str, Any] | None = None


async def discover_verified_tool_contracts(server: MCPServerConfig) -> LiveMcpDiscoveryResult:
    """Launch one stdio MCP server, request ``tools/list``, and validate the result."""
    if server.transport == "http":
        return await _discover_http_verified_tool_contracts(server)

    env = {**os.environ, **server.env}
    try:
        process = await asyncio.create_subprocess_exec(
            server.command,
            *server.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except OSError as exc:
        raise ValueError(f"Failed to start MCP server '{server.name}': {exc}") from exc

    try:
        result = await asyncio.wait_for(
            _discover_verified_tool_contracts(process),
            timeout=MCP_DISCOVERY_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        diagnostics = await _collect_process_diagnostics(process, terminate=True)
        raise ValueError(
            _append_process_diagnostics(
                f"Timed out discovering tools from MCP server '{server.name}' after {MCP_DISCOVERY_TIMEOUT_SECONDS:.0f}s",
                diagnostics,
            )
        ) from exc
    except ValueError as exc:
        diagnostics = await _collect_process_diagnostics(process, terminate=True)
        raise ValueError(_append_process_diagnostics(str(exc), diagnostics)) from exc
    else:
        await _collect_process_diagnostics(process, terminate=True)
        return result
    finally:
        if process.returncode is None:
            await _terminate_process(process)


async def _discover_http_verified_tool_contracts(server: MCPServerConfig) -> LiveMcpDiscoveryResult:
    session = await initialize_http_mcp_session(
        server,
        timeout_seconds=MCP_DISCOVERY_TIMEOUT_SECONDS,
        protocol_version=MCP_PROTOCOL_VERSION,
        client_info={"name": "Beep.AI.Code", "version": "dev"},
    )
    try:
        raw_tools: list[Any] = []
        cursor: str | None = None
        request_id = 2
        while True:
            response = await post_http_jsonrpc_request(
                session,
                request_id=request_id,
                method="tools/list",
                params={} if cursor is None else {"cursor": cursor},
                timeout_seconds=MCP_DISCOVERY_TIMEOUT_SECONDS,
            )
            result = response.get("result")
            if not isinstance(result, dict):
                raise ValueError("MCP server tools/list response must include a JSON object result")
            tools = result.get("tools")
            if not isinstance(tools, list):
                raise ValueError("MCP server tools/list response must include a tools array")
            raw_tools.extend(tools)

            next_cursor = result.get("nextCursor")
            if next_cursor in {None, ""}:
                break
            if not isinstance(next_cursor, str):
                raise ValueError("MCP server tools/list nextCursor must be a string when present")
            cursor = next_cursor
            request_id += 1

        return LiveMcpDiscoveryResult(
            tools=parse_verified_tool_contracts(raw_tools),
            protocol_version=session.protocol_version,
            server_info=session.server_info,
        )
    finally:
        await close_http_mcp_session(session, timeout_seconds=MCP_DISCOVERY_TIMEOUT_SECONDS)


async def _discover_verified_tool_contracts(process: Any) -> LiveMcpDiscoveryResult:
    initialize_response = await _request_message(
        process,
        request_id=1,
        method="initialize",
        params={
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "Beep.AI.Code", "version": "dev"},
        },
    )
    await _send_notification(process, method="notifications/initialized", params={})

    raw_tools: list[Any] = []
    cursor: str | None = None
    request_id = 2
    while True:
        response = await _request_message(
            process,
            request_id=request_id,
            method="tools/list",
            params={} if cursor is None else {"cursor": cursor},
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise ValueError("MCP server tools/list response must include a JSON object result")
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise ValueError("MCP server tools/list response must include a tools array")
        raw_tools.extend(tools)

        next_cursor = result.get("nextCursor")
        if next_cursor in {None, ""}:
            break
        if not isinstance(next_cursor, str):
            raise ValueError("MCP server tools/list nextCursor must be a string when present")
        cursor = next_cursor
        request_id += 1

    result = initialize_response.get("result")
    protocol_version: str | None = None
    server_info: dict[str, Any] | None = None
    if isinstance(result, dict):
        raw_protocol_version = result.get("protocolVersion")
        if isinstance(raw_protocol_version, str) and raw_protocol_version.strip():
            protocol_version = raw_protocol_version.strip()
        raw_server_info = result.get("serverInfo")
        if isinstance(raw_server_info, dict):
            server_info = dict(raw_server_info)

    return LiveMcpDiscoveryResult(
        tools=parse_verified_tool_contracts(raw_tools),
        protocol_version=protocol_version,
        server_info=server_info,
    )


async def _request_message(
    process: Any,
    *,
    request_id: int,
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    await _write_message(
        process,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        },
    )
    while True:
        message = await _read_message(process)
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise ValueError(f"MCP server returned an error for {method}: {message['error']}")
        return message


async def _send_notification(process: Any, *, method: str, params: dict[str, Any]) -> None:
    await _write_message(
        process,
        {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        },
    )


async def _write_message(process: Any, payload: dict[str, Any]) -> None:
    stdin = process.stdin
    if stdin is None:
        raise ValueError("MCP server stdin is unavailable for live tool discovery")
    encoded = json.dumps(payload).encode("utf-8")
    stdin.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii") + encoded)
    await stdin.drain()


async def _read_message(process: Any) -> dict[str, Any]:
    stdout = process.stdout
    if stdout is None:
        raise ValueError("MCP server stdout is unavailable for live tool discovery")

    headers: dict[str, str] = {}
    while True:
        line = await stdout.readline()
        if not line:
            raise ValueError("MCP server closed stdout before sending a complete response")
        if line in {b"\r\n", b"\n"}:
            break
        header = line.decode("ascii", errors="replace").strip()
        if not header:
            break
        key, separator, value = header.partition(":")
        if not separator:
            raise ValueError(f"Invalid MCP header line: {header}")
        headers[key.strip().lower()] = value.strip()

    length_text = headers.get("content-length")
    if length_text is None:
        raise ValueError("MCP response is missing a Content-Length header")
    try:
        body_length = int(length_text)
    except ValueError as exc:
        raise ValueError(f"Invalid MCP Content-Length header: {length_text}") from exc

    try:
        body = await stdout.readexactly(body_length)
    except asyncio.IncompleteReadError as exc:
        raise ValueError("MCP server closed stdout before sending the full response body") from exc

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("MCP server returned invalid JSON during live tool discovery") from exc
    if not isinstance(payload, dict):
        raise ValueError("MCP response body must be a JSON object")
    return payload


async def _terminate_process(process: Any) -> None:
    if process.returncode is not None:
        try:
            await process.communicate()
        except Exception:
            return
        return
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


async def _collect_process_diagnostics(process: Any, *, terminate: bool) -> str:
    if process.returncode is None and not terminate:
        try:
            await asyncio.wait_for(process.wait(), timeout=0.05)
        except TimeoutError:
            pass
        except Exception:
            return ""

    if terminate and process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        except Exception:
            return ""
        try:
            await asyncio.wait_for(process.wait(), timeout=0.2)
        except TimeoutError:
            pass
        except Exception:
            return ""

    try:
        _stdout_bytes, stderr_bytes = await process.communicate()
    except Exception:
        return ""

    stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
    if len(stderr_text) > 500:
        stderr_text = stderr_text[:500].rstrip() + "...[truncated]"
    return stderr_text


def _append_process_diagnostics(message: str, diagnostics: str) -> str:
    details = diagnostics.strip()
    if not details:
        return message
    return f"{message} [stderr: {details}]"


__all__ = [
    "LiveMcpDiscoveryResult",
    "MCP_DISCOVERY_TIMEOUT_SECONDS",
    "discover_verified_tool_contracts",
]