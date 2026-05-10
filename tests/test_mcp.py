"""Tests for MCP bridge config conversion and tool adapters."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from beep.config import MCPServerConfig, MCPToolConfig
from beep.mcp.client import MCP_MAX_OUTPUT_CHARS, MCPClient
from beep.mcp.live_discovery import discover_verified_tool_contracts
from beep.mcp.tool_contracts import parse_verified_tool_contracts


class _MockHttpMcpHandler(BaseHTTPRequestHandler):
    session_id = "session-123"
    mcp_protocol_version = "2025-03-26"

    def do_POST(self) -> None:  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        payload = json.loads(body.decode("utf-8"))
        method = payload.get("method")
        response_headers = {
            "Content-Type": "application/json",
        }
        if method == "initialize":
            response_headers["Mcp-Session-Id"] = self.session_id
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "protocolVersion": self.mcp_protocol_version,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "mock-http", "version": "1.0"},
                    },
                },
                status=200,
                headers=response_headers,
            )
            return
        if method == "notifications/initialized":
            self.send_response(202)
            self.end_headers()
            return
        if method == "tools/list":
            assert self.headers.get("Mcp-Session-Id") == self.session_id
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "http_lookup",
                                "description": "Lookup via HTTP MCP.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                    "required": ["query"],
                                },
                                "annotations": {"readOnlyHint": True},
                            }
                        ]
                    },
                },
                status=200,
                headers=response_headers,
            )
            return
        if method == "tools/call":
            assert self.headers.get("Mcp-Session-Id") == self.session_id
            arguments = (payload.get("params") or {}).get("arguments") or {}
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "content": [
                            {"type": "text", "text": f"http:{arguments.get('query', '')}"}
                        ],
                        "isError": False,
                    },
                },
                status=200,
                headers=response_headers,
            )
            return
        self._send_json(
            {
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            },
            status=200,
            headers=response_headers,
        )

    def do_DELETE(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def log_message(self, _format: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict[str, object], *, status: int, headers: dict[str, str]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class _HttpMcpServer:
    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _MockHttpMcpHandler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}/mcp"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> _HttpMcpServer:
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._server.shutdown()
        self._thread.join(timeout=2)
        self._server.server_close()


def test_mcp_client_from_config_builds_servers_and_tools() -> None:
    servers = [
        MCPServerConfig(
            name="local-mcp",
            command="python",
            args=["-m", "local_mcp"],
            tools=[
                MCPToolConfig(
                    name="query_db",
                    description="Run DB query",
                    parameters={"type": "object", "properties": {"sql": {"type": "string"}}},
                    read_only_safe=True,
                    requires_human_approval=False,
                )
            ],
        )
    ]
    client = MCPClient.from_config(servers)
    assert client.list_servers() == ["local-mcp"]
    tools = client.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "query_db"
    assert tools[0].read_only_safe is True
    assert tools[0].requires_human_approval is False
    adapters = client.to_agent_tools()
    assert adapters[0].read_only_safe is True
    assert adapters[0].requires_human_approval is False


@pytest.mark.asyncio
async def test_mcp_tool_adapter_executes_subprocess() -> None:
    servers = [
        MCPServerConfig(
            name="mock-runner",
            command="python",
            args=[
                "-c",
                (
                    "import json,sys;"
                    "req=json.loads(sys.stdin.read());"
                    "print(json.dumps({'success':True,'output':'ok:'+req['tool']}))"
                ),
            ],
            tools=[MCPToolConfig(name="lookup", parameters={"type": "object"})],
        )
    ]
    client = MCPClient.from_config(servers)
    adapters = client.to_agent_tools()
    assert len(adapters) == 1
    result = await adapters[0].execute(q="x")
    assert result.success is True
    assert result.output == "ok:lookup"


@pytest.mark.asyncio
async def test_mcp_tool_adapter_reports_subprocess_error() -> None:
    servers = [
        MCPServerConfig(
            name="mock-fail",
            command="python",
            args=["-c", "import sys; sys.stderr.write('boom'); sys.exit(1)"],
            tools=[MCPToolConfig(name="lookup", parameters={"type": "object"})],
        )
    ]
    client = MCPClient.from_config(servers)
    adapter = client.to_agent_tools()[0]
    result = await adapter.execute(q="x")
    assert result.success is False
    assert "boom" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_mcp_tool_adapter_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProcess:
        returncode = 0

        async def communicate(self, *_args, **_kwargs):
            await asyncio.sleep(0.01)
            return b"", b""

        def kill(self) -> None:
            return None

    async def fake_create_subprocess_exec(*_args, **_kwargs):
        return FakeProcess()

    async def fake_wait_for(coro, *_args, **_kwargs):
        coro.close()
        raise TimeoutError

    monkeypatch.setattr(
        "beep.mcp.client.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    monkeypatch.setattr("beep.mcp.client.asyncio.wait_for", fake_wait_for)

    servers = [
        MCPServerConfig(
            name="mock-timeout",
            command="python",
            tools=[MCPToolConfig(name="lookup", parameters={"type": "object"})],
        )
    ]
    client = MCPClient.from_config(servers)
    result = await client.to_agent_tools()[0].execute(q="x")
    assert result.success is False
    assert "timed out" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_mcp_tool_adapter_reports_transport_failure_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        returncode = 1

        def __init__(self) -> None:
            self.kill_called = False
            self._communicate_calls = 0

        async def communicate(self, *_args, **_kwargs):
            self._communicate_calls += 1
            if self._communicate_calls == 1:
                raise BrokenPipeError("pipe closed")
            return b"", b""

        def kill(self) -> None:
            self.kill_called = True

    process = FakeProcess()

    async def fake_create_subprocess_exec(*_args, **_kwargs):
        return process

    async def fake_wait_for(coro, *_args, **_kwargs):
        return await coro

    monkeypatch.setattr(
        "beep.mcp.client.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    monkeypatch.setattr("beep.mcp.client.asyncio.wait_for", fake_wait_for)

    servers = [
        MCPServerConfig(
            name="mock-transport",
            command="python",
            tools=[MCPToolConfig(name="lookup", parameters={"type": "object"})],
        )
    ]
    client = MCPClient.from_config(servers)
    result = await client.to_agent_tools()[0].execute(q="x")

    assert result.success is False
    assert "transport failure" in (result.error or "").lower()
    assert process.kill_called is True


@pytest.mark.asyncio
async def test_mcp_tool_adapter_truncates_large_output() -> None:
    payload = "x" * (MCP_MAX_OUTPUT_CHARS + 100)
    servers = [
        MCPServerConfig(
            name="mock-large",
            command="python",
            args=["-c", f"print('{payload}')"],
            tools=[MCPToolConfig(name="lookup", parameters={"type": "object"})],
        )
    ]
    client = MCPClient.from_config(servers)
    result = await client.to_agent_tools()[0].execute(q="x")
    assert result.success is True
    assert result.output.endswith("...[truncated]")


@pytest.mark.asyncio
async def test_mcp_tool_adapter_logs_start_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    def _capture(event_name: str, **_kwargs) -> None:
        events.append(event_name)

    monkeypatch.setattr("beep.mcp.client.log_event", _capture)

    servers = [
        MCPServerConfig(
            name="mock-runner",
            command="python",
            args=[
                "-c",
                (
                    "import json,sys;"
                    "req=json.loads(sys.stdin.read());"
                    "print(json.dumps({'success':True,'output':'ok:'+req['tool']}))"
                ),
            ],
            tools=[MCPToolConfig(name="lookup", parameters={"type": "object"})],
        )
    ]
    client = MCPClient.from_config(servers)
    result = await client.to_agent_tools()[0].execute(q="x")
    assert result.success is True
    assert "mcp.tool.start" in events
    assert "mcp.tool.success" in events


@pytest.mark.asyncio
async def test_mcp_tool_adapter_logs_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    def _capture(event_name: str, **_kwargs) -> None:
        events.append(event_name)

    class FakeProcess:
        returncode = 0

        async def communicate(self, *_args, **_kwargs):
            await asyncio.sleep(0.01)
            return b"", b""

        def kill(self) -> None:
            return None

    async def fake_create_subprocess_exec(*_args, **_kwargs):
        return FakeProcess()

    async def fake_wait_for(coro, *_args, **_kwargs):
        coro.close()
        raise TimeoutError

    monkeypatch.setattr("beep.mcp.client.log_event", _capture)
    monkeypatch.setattr(
        "beep.mcp.client.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    monkeypatch.setattr("beep.mcp.client.asyncio.wait_for", fake_wait_for)

    servers = [
        MCPServerConfig(
            name="mock-timeout",
            command="python",
            tools=[MCPToolConfig(name="lookup", parameters={"type": "object"})],
        )
    ]
    client = MCPClient.from_config(servers)
    result = await client.to_agent_tools()[0].execute(q="x")
    assert result.success is False
    assert "timed out" in (result.error or "").lower()


def test_parse_verified_tool_contracts_accepts_result_tools_shape() -> None:
    tools = parse_verified_tool_contracts(
        {
            "result": {
                "tools": [
                    {
                        "name": "browser_navigate",
                        "description": "Navigate to a URL.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"url": {"type": "string"}},
                            "required": ["url"],
                        },
                    }
                ]
            }
        }
    )

    assert [tool.name for tool in tools] == ["browser_navigate"]
    assert tools[0].parameters["required"] == ["url"]
    assert tools[0].requires_human_approval is True


def test_parse_verified_tool_contracts_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="duplicate tool name"):
        parse_verified_tool_contracts(
            {
                "tools": [
                    {"name": "browser_snapshot", "inputSchema": {}},
                    {"name": "browser_snapshot", "inputSchema": {}},
                ]
            }
        )


@pytest.mark.asyncio
async def test_discover_verified_tool_contracts_reads_live_stdio_tools(tmp_path: Path) -> None:
    server_script = tmp_path / "mock_live_mcp.py"
    server_script.write_text(
        (
            "import json, sys\n"
            "\n"
            "def read_message():\n"
            "    headers = {}\n"
            "    while True:\n"
            "        line = sys.stdin.buffer.readline()\n"
            "        if not line:\n"
            "            return None\n"
            "        if line in (b'\\r\\n', b'\\n'):\n"
            "            break\n"
            "        key, _, value = line.decode('ascii').partition(':')\n"
            "        headers[key.strip().lower()] = value.strip()\n"
            "    body = sys.stdin.buffer.read(int(headers['content-length']))\n"
            "    return json.loads(body.decode('utf-8'))\n"
            "\n"
            "def write_message(payload):\n"
            "    encoded = json.dumps(payload).encode('utf-8')\n"
            "    sys.stdout.buffer.write(f'Content-Length: {len(encoded)}\\r\\n\\r\\n'.encode('ascii'))\n"
            "    sys.stdout.buffer.write(encoded)\n"
            "    sys.stdout.buffer.flush()\n"
            "\n"
            "while True:\n"
            "    message = read_message()\n"
            "    if message is None:\n"
            "        break\n"
            "    method = message.get('method')\n"
            "    if method == 'initialize':\n"
            "        write_message({'jsonrpc': '2.0', 'id': message['id'], 'result': {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'mock-live', 'version': '1.0'}}})\n"
            "    elif method == 'notifications/initialized':\n"
            "        continue\n"
            "    elif method == 'tools/list':\n"
            "        cursor = (message.get('params') or {}).get('cursor')\n"
            "        if cursor is None:\n"
            "            write_message({'jsonrpc': '2.0', 'id': message['id'], 'result': {'tools': [{'name': 'browser_navigate', 'description': 'Navigate to a URL.', 'inputSchema': {'type': 'object', 'properties': {'url': {'type': 'string'}}, 'required': ['url']}, 'annotations': {'readOnlyHint': True}}], 'nextCursor': 'page-2'}})\n"
            "        else:\n"
            "            write_message({'jsonrpc': '2.0', 'id': message['id'], 'result': {'tools': [{'name': 'browser_snapshot', 'description': 'Capture the page state.', 'inputSchema': {'type': 'object', 'properties': {}}}]}})\n"
            "    else:\n"
            "        write_message({'jsonrpc': '2.0', 'id': message.get('id'), 'error': {'code': -32601, 'message': 'Unknown method'}})\n"
        ),
        encoding="utf-8",
    )

    discovery_result = await discover_verified_tool_contracts(
        MCPServerConfig(
            name="mock-live",
            command=sys.executable,
            args=[str(server_script)],
        )
    )

    tools = discovery_result.tools
    assert [tool.name for tool in tools] == ["browser_navigate", "browser_snapshot"]
    assert tools[0].read_only_safe is True
    assert discovery_result.protocol_version == "2024-11-05"
    assert discovery_result.server_info == {"name": "mock-live", "version": "1.0"}


@pytest.mark.asyncio
async def test_discover_verified_tool_contracts_reads_http_tools() -> None:
    with _HttpMcpServer() as server:
        discovery_result = await discover_verified_tool_contracts(
            MCPServerConfig(
                name="mock-http",
                transport="http",
                url=server.url,
                headers={"Authorization": "Bearer token"},
            )
        )

    assert [tool.name for tool in discovery_result.tools] == ["http_lookup"]
    assert discovery_result.tools[0].read_only_safe is True
    assert discovery_result.protocol_version == "2025-03-26"
    assert discovery_result.server_info == {"name": "mock-http", "version": "1.0"}


@pytest.mark.asyncio
async def test_mcp_http_tool_adapter_executes_tools_call() -> None:
    with _HttpMcpServer() as server:
        client = MCPClient.from_config(
            [
                MCPServerConfig(
                    name="mock-http",
                    transport="http",
                    url=server.url,
                    headers={"Authorization": "Bearer token"},
                    tools=[
                        MCPToolConfig(
                            name="http_lookup",
                            description="Lookup via HTTP.",
                            parameters={
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                            },
                            read_only_safe=True,
                            requires_human_approval=False,
                        )
                    ],
                )
            ]
        )
        result = await client.to_agent_tools()[0].execute(query="abc")

    assert result.success is True
    assert result.output == "http:abc"


@pytest.mark.asyncio
async def test_discover_verified_tool_contracts_surfaces_server_stderr(tmp_path: Path) -> None:
    failing_server = tmp_path / "failing_live_mcp.py"
    failing_server.write_text(
        "import sys\n"
        "sys.stderr.write('missing MCP_API_KEY')\n"
        "sys.stderr.flush()\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing MCP_API_KEY"):
        await discover_verified_tool_contracts(
            MCPServerConfig(
                name="failing-live",
                command=sys.executable,
                args=[str(failing_server)],
            )
        )
