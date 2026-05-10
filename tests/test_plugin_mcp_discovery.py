"""Focused tests for file-backed plugin and MCP discovery."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from beep.agent.tools.factory import build_agent_tools
from beep.cli import app
from beep.config import BeepConfig
from beep.mcp.client import MCPClient
from beep.mcp.discovery import resolve_mcp_configuration
from beep.mcp.presets import get_mcp_preset
from beep.plugins.registry import PluginRegistry
from beep.plugins.runtime import load_runtime_plugins


def _set_home(monkeypatch, home: Path) -> None:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def test_plugin_runtime_includes_workspace_manifest_paths(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    _set_home(monkeypatch, home)

    manifest_path = workspace / ".beep" / "plugins.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"plugin_paths": ["custom_plugins"]}), encoding="utf-8")

    runtime = load_runtime_plugins(workspace, enabled=False)
    assert workspace / "custom_plugins" in runtime.searched_paths


def test_resolve_mcp_configuration_reads_workspace_server_files(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    _set_home(monkeypatch, home)

    server_path = workspace / ".beep" / "mcp" / "firecrawl.json"
    server_path.parent.mkdir(parents=True, exist_ok=True)
    server_path.write_text(
        json.dumps(
            {
                "name": "firecrawl",
                "command": "npx",
                "args": ["-y", "firecrawl-mcp"],
                "env": {"FIRECRAWL_API_KEY": "token"},
                "tools": [],
            }
        ),
        encoding="utf-8",
    )

    resolved = resolve_mcp_configuration(BeepConfig(), workspace)
    assert resolved.enabled is True
    assert [server.name for server in resolved.servers] == ["firecrawl"]
    assert resolved.sources["firecrawl"].endswith("firecrawl.json")


def test_resolve_mcp_configuration_reads_vscode_mcp_json(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    _set_home(monkeypatch, home)

    vscode_path = workspace / ".vscode" / "mcp.json"
    vscode_path.parent.mkdir(parents=True, exist_ok=True)
    vscode_path.write_text(
        json.dumps(
            {
                "servers": {
                    "chrome": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "chrome-devtools-mcp@latest"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    resolved = resolve_mcp_configuration(BeepConfig(), workspace)
    assert [server.name for server in resolved.servers] == ["chrome"]


def test_resolve_mcp_configuration_reads_http_vscode_mcp_json(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    _set_home(monkeypatch, home)

    vscode_path = workspace / ".vscode" / "mcp.json"
    vscode_path.parent.mkdir(parents=True, exist_ok=True)
    vscode_path.write_text(
        json.dumps(
            {
                "servers": {
                    "remote-mcp": {
                        "type": "http",
                        "url": "http://127.0.0.1:8765/mcp",
                        "headers": {"Authorization": "Bearer token"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    resolved = resolve_mcp_configuration(BeepConfig(), workspace)
    assert [server.name for server in resolved.servers] == ["remote-mcp"]
    assert resolved.servers[0].transport == "http"
    assert resolved.servers[0].url == "http://127.0.0.1:8765/mcp"
    assert resolved.servers[0].headers == {"Authorization": "Bearer token"}


def test_mcp_init_cli_generates_http_server_file(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "remote-tools",
            "--url",
            "https://example.test/mcp",
            "--header",
            "Authorization=Bearer token",
        ],
    )
    assert init_result.exit_code == 0

    payload = json.loads((workspace / ".beep" / "mcp" / "remote-tools.json").read_text(encoding="utf-8"))
    assert payload["transport"] == "http"
    assert payload["url"] == "https://example.test/mcp"
    assert payload["headers"] == {"Authorization": "Bearer token"}


def test_plugins_add_path_cli_updates_manifest(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    runner = CliRunner()
    result = runner.invoke(app, ["plugins", "add-path", "extra_plugins", "--scope", "workspace"])
    assert result.exit_code == 0

    runtime = load_runtime_plugins(workspace, enabled=False)
    assert workspace / "extra_plugins" in runtime.searched_paths


def test_mcp_init_cli_generates_server_file_and_list_finds_it(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "firecrawl",
            "--preset",
            "firecrawl",
            "--env",
            "FIRECRAWL_API_KEY=token",
            "--scope",
            "workspace",
        ],
    )
    assert init_result.exit_code == 0
    server_path = workspace / ".beep" / "mcp" / "firecrawl.json"
    assert server_path.exists()

    payload = json.loads(server_path.read_text(encoding="utf-8"))
    assert payload["command"] == "npx"
    assert payload["args"] == ["-y", "firecrawl-mcp"]
    assert payload["metadata"]["preset"] == "firecrawl"
    assert payload["metadata"]["verification_scope"] == "launch-and-tool-metadata"
    assert payload["metadata"]["tool_contracts_included"] is True
    assert "firecrawl_search" in {tool["name"] for tool in payload["tools"]}

    list_result = runner.invoke(app, ["mcp", "list"])
    assert list_result.exit_code == 0
    assert "firecrawl" in (list_result.stdout or "")


def test_mcp_presets_cli_lists_verified_presets(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    runner = CliRunner()
    result = runner.invoke(app, ["mcp", "presets"])

    assert result.exit_code == 0
    stdout = result.stdout or ""
    assert "firecrawl" in stdout
    assert "playwright" in stdout
    assert "chrome-devtools" in stdout


def test_chrome_preset_uses_windows_cmd_wrapper() -> None:
    preset = get_mcp_preset("chrome")

    server_config, metadata, missing_required_env = preset.build_server_definition(
        is_windows=True,
    )

    assert server_config.command == "cmd"
    assert server_config.args == ["/c", "npx", "-y", "chrome-devtools-mcp@latest"]
    assert metadata["preset"] == "chrome-devtools"
    assert missing_required_env == []


def test_perplexity_preset_exposes_static_tools_to_mcp_client_and_agent(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "perplexity",
            "--preset",
            "perplexity",
            "--env",
            "PERPLEXITY_API_KEY=token",
        ],
    )
    assert init_result.exit_code == 0

    resolved = resolve_mcp_configuration(BeepConfig(), workspace)
    client = MCPClient.from_config(resolved.servers)
    assert {tool.name for tool in client.list_tools()} >= {
        "perplexity_search",
        "perplexity_ask",
        "perplexity_research",
        "perplexity_reason",
    }

    runtime = load_runtime_plugins(workspace, enabled=False)
    runtime = runtime.__class__(
        registry=PluginRegistry(),
        searched_paths=runtime.searched_paths,
        loaded_count=0,
        discovery_errors=[],
    )
    tools = build_agent_tools(
        workspace_root=workspace,
        plugin_runtime=runtime,
        mcp_enabled=resolved.enabled,
        mcp_servers=resolved.servers,
    )
    assert {tool.name for tool in tools} >= {
        "perplexity_search",
        "perplexity_ask",
        "perplexity_research",
        "perplexity_reason",
    }


def test_agent_command_uses_resolved_mcp_servers(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    server_path = workspace / ".beep" / "mcp" / "chrome.json"
    server_path.parent.mkdir(parents=True, exist_ok=True)
    server_path.write_text(
        json.dumps(
            {
                "name": "chrome",
                "command": "npx",
                "args": ["-y", "chrome-devtools-mcp@latest"],
                "tools": [],
            }
        ),
        encoding="utf-8",
    )

    import beep.commands.agent as agent_commands

    fake_run_agent = AsyncMock()
    monkeypatch.setattr(agent_commands, "ensure_agent_configured", lambda: BeepConfig())
    monkeypatch.setattr(agent_commands, "run_agent", fake_run_agent)

    agent_commands.agent_cmd("inspect the workspace")

    kwargs = fake_run_agent.await_args.kwargs
    assert kwargs["mcp_enabled"] is True
    assert [server.name for server in kwargs["mcp_servers"]] == ["chrome"]


def test_mcp_verify_tools_cli_updates_launch_only_preset_definition(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "playwright",
            "--preset",
            "playwright",
        ],
    )
    assert init_result.exit_code == 0

    tool_contract_path = workspace / "playwright-tools.json"
    tool_contract_path.write_text(
        json.dumps(
            {
                "result": {
                    "tools": [
                        {
                            "name": "browser_navigate",
                            "description": "Navigate the browser to a URL.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"url": {"type": "string"}},
                                "required": ["url"],
                            },
                        },
                        {
                            "name": "browser_snapshot",
                            "description": "Capture the current page state.",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    verify_result = runner.invoke(
        app,
        [
            "mcp",
            "verify-tools",
            "playwright",
            "--from-file",
            str(tool_contract_path),
        ],
    )

    assert verify_result.exit_code == 0
    payload = json.loads((workspace / ".beep" / "mcp" / "playwright.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["verification_scope"] == "launch-and-tool-metadata"
    assert payload["metadata"]["tool_contracts_included"] is True
    assert payload["metadata"]["verified_tool_contract_source"] == str(tool_contract_path)
    assert {tool["name"] for tool in payload["tools"]} == {"browser_navigate", "browser_snapshot"}

    resolved = resolve_mcp_configuration(BeepConfig(), workspace)
    client = MCPClient.from_config(resolved.servers)
    assert {tool.name for tool in client.list_tools()} >= {"browser_navigate", "browser_snapshot"}


def test_mcp_verify_tools_cli_discovers_live_tool_contracts(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    server_script = workspace / "mock_live_mcp.py"
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

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "mock-live",
            "--command",
            sys.executable,
            "--arg",
            str(server_script),
        ],
    )
    assert init_result.exit_code == 0

    verify_result = runner.invoke(
        app,
        [
            "mcp",
            "verify-tools",
            "mock-live",
            "--discover",
        ],
    )

    assert verify_result.exit_code == 0
    payload = json.loads((workspace / ".beep" / "mcp" / "mock-live.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["verified_tool_contract_source"] == "live:mock-live"
    assert payload["metadata"]["verified_tool_protocol_version"] == "2024-11-05"
    assert payload["metadata"]["verified_tool_server_info"] == {"name": "mock-live", "version": "1.0"}
    assert payload["tools"][0]["read_only_safe"] is True
    assert {tool["name"] for tool in payload["tools"]} == {"browser_navigate", "browser_snapshot"}


def test_mcp_verify_tools_cli_surfaces_live_discovery_stderr(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    failing_server = workspace / "failing_live_mcp.py"
    failing_server.write_text(
        "import sys\n"
        "sys.stderr.write('missing MCP_API_KEY')\n"
        "sys.stderr.flush()\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "failing-live",
            "--command",
            sys.executable,
            "--arg",
            str(failing_server),
        ],
    )
    assert init_result.exit_code == 0

    verify_result = runner.invoke(
        app,
        [
            "mcp",
            "verify-tools",
            "failing-live",
            "--discover",
        ],
    )

    assert verify_result.exit_code == 1
    stdout = verify_result.stdout or ""
    assert "missing MCP_API_KEY" in stdout


def test_mcp_verify_tools_cli_surfaces_live_discovery_timeout(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    hanging_server = workspace / "hanging_live_mcp.py"
    hanging_server.write_text(
        "import time\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "hanging-live",
            "--command",
            sys.executable,
            "--arg",
            str(hanging_server),
        ],
    )
    assert init_result.exit_code == 0

    verify_result = runner.invoke(
        app,
        [
            "mcp",
            "verify-tools",
            "hanging-live",
            "--discover",
        ],
    )

    assert verify_result.exit_code == 1
    stdout = verify_result.stdout or ""
    assert "Timed out discovering tools from MCP server 'hanging-live'" in stdout


def test_mcp_verify_tools_cli_surfaces_malformed_live_response(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    malformed_server = workspace / "malformed_live_mcp.py"
    malformed_server.write_text(
        "import sys\n"
        "sys.stdout.write('not-a-header\\n\\n')\n"
        "sys.stdout.flush()\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "malformed-live",
            "--command",
            sys.executable,
            "--arg",
            str(malformed_server),
        ],
    )
    assert init_result.exit_code == 0

    verify_result = runner.invoke(
        app,
        [
            "mcp",
            "verify-tools",
            "malformed-live",
            "--discover",
        ],
    )

    assert verify_result.exit_code == 1
    stdout = verify_result.stdout or ""
    assert "Invalid MCP header line: not-a-header" in stdout


def test_mcp_verify_tools_cli_surfaces_invalid_json_live_response(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    home.mkdir()
    workspace.mkdir()
    (workspace / ".git").mkdir()
    _set_home(monkeypatch, home)
    monkeypatch.chdir(workspace)

    invalid_json_server = workspace / "invalid_json_live_mcp.py"
    invalid_json_server.write_text(
        "import sys\n"
        "sys.stdout.buffer.write(b'Content-Length: 8\\r\\n\\r\\nnot-json')\n"
        "sys.stdout.buffer.flush()\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    init_result = runner.invoke(
        app,
        [
            "mcp",
            "init",
            "invalid-json-live",
            "--command",
            sys.executable,
            "--arg",
            str(invalid_json_server),
        ],
    )
    assert init_result.exit_code == 0

    verify_result = runner.invoke(
        app,
        [
            "mcp",
            "verify-tools",
            "invalid-json-live",
            "--discover",
        ],
    )

    assert verify_result.exit_code == 1
    stdout = verify_result.stdout or ""
    assert "MCP server returned invalid JSON during live tool discovery" in stdout