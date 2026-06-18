"""Language Server Protocol client — stdio JSON-RPC.

Communicates with LSP servers over stdin/stdout using a lightweight
JSON-RPC 2.0 implementation. Supports basic lifecycle: initialize,
didOpen, diagnostics, hover, and shutdown.
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Any


class LspClient:
    def __init__(self, command: list[str], root_uri: str) -> None:
        self._command = command
        self._root_uri = root_uri
        self._process: subprocess.Popen[bytes] | None = None
        self._seq = 0
        self._lock = threading.Lock()
        self._responses: dict[int, dict[str, Any]] = {}
        self._reader_thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        params: dict[str, Any] = {
            "processId": None,
            "rootUri": self._root_uri,
            "capabilities": {
                "textDocument": {
                    "diagnostic": {"dynamicRegistration": True},
                    "hover": {"dynamicRegistration": True},
                }
            },
        }
        self._request("initialize", params)
        self._notify("initialized", {})

    def stop(self) -> None:
        self._running = False
        if self._process and self._process.poll() is None:
            try:
                self._request("shutdown", {})
                self._notify("exit", {})
            except Exception:
                pass
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None
        self._reader_thread = None

    def diagnostics(self, file_path: Path) -> list[dict[str, Any]]:
        uri = file_path.as_uri()
        content = file_path.read_text(encoding="utf-8")
        self._notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": _guess_language(file_path),
                    "version": 1,
                    "text": content,
                }
            },
        )
        result = self._request(
            "textDocument/diagnostic",
            {"textDocument": {"uri": uri}},
        )
        if not result:
            return []
        items = result.get("items", [])
        return [
            {
                "range": i.get("range", {}),
                "severity": i.get("severity", 1),
                "message": i.get("message", ""),
                "source": i.get("source", ""),
            }
            for i in items
        ]

    def hover(self, file_path: Path, line: int, character: int) -> str | None:
        uri = file_path.as_uri()
        result = self._request(
            "textDocument/hover",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            },
        )
        if not result:
            return None
        contents = result.get("contents", {})
        if isinstance(contents, dict):
            return contents.get("value", str(contents))
        if isinstance(contents, str):
            return contents
        return None

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
        self._send(msg)

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            self._seq += 1
            req_id = self._seq
        msg = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        self._send(msg)
        for _ in range(50):
            with self._lock:
                resp = self._responses.pop(req_id, None)
            if resp is not None:
                if "error" in resp:
                    return None
                return resp.get("result", {})
            import time

            time.sleep(0.1)
        return None

    def _send(self, message: str) -> None:
        if self._process is None or self._process.stdin is None:
            return
        header = f"Content-Length: {len(message.encode('utf-8'))}\r\n\r\n"
        try:
            self._process.stdin.write((header + message).encode("utf-8"))
            self._process.stdin.flush()
        except Exception:
            pass

    def _read_loop(self) -> None:
        if self._process is None or self._process.stdout is None:
            return
        buffer = b""
        while self._running:
            try:
                char = self._process.stdout.read(1)
                if not char:
                    break
                buffer += char
                if b"\r\n\r\n" in buffer:
                    header_end = buffer.index(b"\r\n\r\n")
                    header = buffer[:header_end].decode("utf-8")
                    body_start = header_end + 4
                    buffer = buffer[body_start:]
                    length = 0
                    for line in header.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            length = int(line.split(":")[1].strip())
                    while len(buffer) < length and self._running:
                        chunk = self._process.stdout.read(length - len(buffer))
                        if not chunk:
                            break
                        buffer += chunk
                    if len(buffer) < length:
                        break
                    body = buffer[:length].decode("utf-8")
                    buffer = buffer[length:]
                    try:
                        msg = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    req_id = msg.get("id")
                    if req_id is not None:
                        with self._lock:
                            self._responses[req_id] = msg
            except Exception:
                break


def _guess_language(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    language_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescriptreact",
        ".js": "javascript",
        ".jsx": "javascriptreact",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".rb": "ruby",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".vue": "vue",
        ".svelte": "svelte",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".css": "css",
        ".html": "html",
        ".sql": "sql",
    }
    return language_map.get(ext, "plaintext")
