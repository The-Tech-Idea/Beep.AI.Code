"""Tests for LSP client, registry, and diagnostics tool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from beep.agent.tools.lsp_diagnostics import LspDiagnosticsTool
from beep.lsp.client import LspClient, _guess_language
from beep.lsp.registry import available_languages, find_server_command


class TestGuessLanguage:
    def test_python(self) -> None:
        assert _guess_language(Path("test.py")) == "python"

    def test_typescript(self) -> None:
        assert _guess_language(Path("app.ts")) == "typescript"

    def test_rust(self) -> None:
        assert _guess_language(Path("main.rs")) == "rust"

    def test_javascript(self) -> None:
        assert _guess_language(Path("app.js")) == "javascript"

    def test_unknown(self) -> None:
        assert _guess_language(Path("data.xyz")) == "plaintext"


class TestRegistry:
    def test_available_languages(self) -> None:
        langs = available_languages()
        assert "python" in langs
        assert "rust" in langs
        assert "typescript" in langs

    def test_find_server_for_python_mocked(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/pyright-langserver"):
            cmd = find_server_command(Path("test.py"))
            assert cmd is not None
            assert cmd[0] == "pyright-langserver"

    def test_find_server_none(self) -> None:
        with patch("shutil.which", return_value=None):
            cmd = find_server_command(Path("test.py"))
            assert cmd is None


class TestLspClient:
    def test_initialization_sends_initialize(self) -> None:
        client = LspClient(["echo"], "file:///root")
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            client.start()
            mock_popen.assert_called_once()
            mock_process.stdin.write.assert_called()

    def test_stop_cleans_up(self) -> None:
        client = LspClient(["echo"], "file:///root")
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            client.start()
            client.stop()
            assert client._process is None


class TestLspDiagnosticsTool:
    def test_tool_is_read_only_safe(self) -> None:
        tool = LspDiagnosticsTool(workspace_root=Path("/tmp"))
        assert tool.read_only_safe is True

    def test_tool_has_name(self) -> None:
        tool = LspDiagnosticsTool(workspace_root=Path("/tmp"))
        assert tool.name == "lsp_diagnostics"
        assert tool.description

    def test_parameters(self) -> None:
        tool = LspDiagnosticsTool(workspace_root=Path("/tmp"))
        params = tool.parameters
        assert "file_path" in params
