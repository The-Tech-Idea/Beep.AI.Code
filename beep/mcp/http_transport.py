"""Shared streamable HTTP helpers for MCP requests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from beep.config import MCPServerConfig


@dataclass
class HttpMcpSession:
    """One logical MCP HTTP session."""

    server_name: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    session_id: str | None = None
    protocol_version: str | None = None
    server_info: dict[str, Any] | None = None


async def initialize_http_mcp_session(
    server: MCPServerConfig,
    *,
    timeout_seconds: float,
    protocol_version: str,
    client_info: dict[str, str],
) -> HttpMcpSession:
    """Initialize a streamable HTTP MCP session and send `initialized`."""
    session = HttpMcpSession(
        server_name=server.name,
        url=str(server.url or ""),
        headers=dict(server.headers),
    )
    response = await post_http_jsonrpc_request(
        session,
        request_id=1,
        method="initialize",
        params={
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": client_info,
        },
        timeout_seconds=timeout_seconds,
    )
    result = response.get("result")
    if not isinstance(result, dict):
        raise ValueError("MCP HTTP initialize response must include a JSON object result")
    raw_protocol_version = result.get("protocolVersion")
    if isinstance(raw_protocol_version, str) and raw_protocol_version.strip():
        session.protocol_version = raw_protocol_version.strip()
    raw_server_info = result.get("serverInfo")
    if isinstance(raw_server_info, dict):
        session.server_info = dict(raw_server_info)

    await post_http_jsonrpc_notification(
        session,
        method="notifications/initialized",
        params={},
        timeout_seconds=timeout_seconds,
    )
    return session


async def post_http_jsonrpc_request(
    session: HttpMcpSession,
    *,
    request_id: int,
    method: str,
    params: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Send one JSON-RPC request over streamable HTTP and return the matching response."""
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=10.0)) as client:
        request_headers = _build_http_headers(session, include_json_body=True)
        async with client.stream(
            "POST",
            session.url,
            headers=request_headers,
            json=payload,
        ) as response:
            _update_session_headers(session, response)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(
                    _format_http_status_error(session.server_name, method, exc.response)
                ) from exc
            content_type = response.headers.get("Content-Type", "")
            lowered_content_type = content_type.lower()
            if lowered_content_type.startswith("application/json"):
                raw_payload = await response.aread()
                parsed = _parse_json_payload(raw_payload, context=f"{method} HTTP response")
                return _select_matching_jsonrpc_response(parsed, request_id=request_id, method=method)
            if lowered_content_type.startswith("text/event-stream"):
                return await _read_sse_jsonrpc_response(response, request_id=request_id, method=method)
            raise ValueError(
                f"MCP HTTP request {method} for '{session.server_name}' returned unsupported content type: {content_type or '<missing>'}"
            )


async def post_http_jsonrpc_notification(
    session: HttpMcpSession,
    *,
    method: str,
    params: dict[str, Any],
    timeout_seconds: float,
) -> None:
    """Send one JSON-RPC notification over streamable HTTP."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=10.0)) as client:
        response = await client.post(
            session.url,
            headers=_build_http_headers(session, include_json_body=True),
            json=payload,
        )
        _update_session_headers(session, response)
        if response.status_code not in {200, 202, 204}:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(
                    _format_http_status_error(session.server_name, method, exc.response)
                ) from exc


async def close_http_mcp_session(session: HttpMcpSession, *, timeout_seconds: float) -> None:
    """Best-effort streamable HTTP session cleanup."""
    if not session.session_id:
        return
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=10.0)) as client:
            await client.delete(
                session.url,
                headers=_build_http_headers(session, include_json_body=False),
            )
    except Exception:
        return


def _build_http_headers(session: HttpMcpSession, *, include_json_body: bool) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        **session.headers,
    }
    if include_json_body:
        headers.setdefault("Content-Type", "application/json")
    if session.session_id:
        headers["Mcp-Session-Id"] = session.session_id
    return headers


def _update_session_headers(session: HttpMcpSession, response: httpx.Response) -> None:
    session_id = response.headers.get("Mcp-Session-Id")
    if session_id:
        session.session_id = session_id


def _parse_json_payload(raw_payload: bytes, *, context: str) -> Any:
    try:
        return json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"MCP {context} returned invalid JSON") from exc


def _select_matching_jsonrpc_response(payload: Any, *, request_id: int, method: str) -> dict[str, Any]:
    for message in _iter_jsonrpc_messages(payload):
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise ValueError(f"MCP server returned an error for {method}: {message['error']}")
        return message
    raise ValueError(f"MCP HTTP request {method} returned no response for id {request_id}")


def _iter_jsonrpc_messages(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [message for message in payload if isinstance(message, dict)]
    return []


async def _read_sse_jsonrpc_response(
    response: httpx.Response,
    *,
    request_id: int,
    method: str,
) -> dict[str, Any]:
    data_lines: list[str] = []
    async for line in response.aiter_lines():
        if line == "":
            matched = _maybe_parse_sse_event(data_lines, request_id=request_id, method=method)
            data_lines.clear()
            if matched is not None:
                return matched
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    matched = _maybe_parse_sse_event(data_lines, request_id=request_id, method=method)
    if matched is not None:
        return matched
    raise ValueError(f"MCP HTTP stream for {method} ended before returning a response")


def _maybe_parse_sse_event(
    data_lines: list[str],
    *,
    request_id: int,
    method: str,
) -> dict[str, Any] | None:
    if not data_lines:
        return None
    payload = _parse_json_payload("\n".join(data_lines).encode("utf-8"), context=f"{method} SSE event")
    for message in _iter_jsonrpc_messages(payload):
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise ValueError(f"MCP server returned an error for {method}: {message['error']}")
        return message
    return None


def _format_http_status_error(server_name: str, method: str, response: httpx.Response) -> str:
    response_text = response.text.strip()
    suffix = f": {response_text}" if response_text else ""
    return (
        f"MCP HTTP request {method} for '{server_name}' failed with "
        f"HTTP {response.status_code}{suffix}"
    )


__all__ = [
    "HttpMcpSession",
    "close_http_mcp_session",
    "initialize_http_mcp_session",
    "post_http_jsonrpc_notification",
    "post_http_jsonrpc_request",
]