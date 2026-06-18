"""LSP diagnostics tool for the agent — feeds language server diagnostics to the model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult


class LspDiagnosticsTool(BaseTool):
    read_only_safe = True

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "lsp_diagnostics"

    @property
    def description(self) -> str:
        return "Get diagnostics (errors, warnings, hints) from a language server for a file."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "Relative or absolute path to the file to analyze.",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return []

    async def execute(self, *, file_path: str = "", **kwargs: Any) -> ToolResult:  # noqa: ARG002
        path = (
            self._workspace_root / file_path
            if not Path(file_path).is_absolute()
            else Path(file_path)
        )
        if not path.exists():
            return ToolResult(success=True, output=f"File not found: {file_path}")

        try:
            from beep.lsp.registry import find_server_command
        except ImportError:
            return ToolResult(success=True, output="LSP support is not available.")

        command = find_server_command(path)
        if command is None:
            return ToolResult(
                success=True,
                output=f"No LSP server found for '{path.suffix}'. "
                f"Install a language server (e.g. pyright for Python).",
            )

        client = None
        try:
            from beep.lsp.client import LspClient

            root_uri = self._workspace_root.as_uri()
            client = LspClient(command, root_uri)
            client.start()
            diags = client.diagnostics(path)
        except Exception as exc:
            return ToolResult(success=True, output=f"LSP diagnostics failed: {exc}")
        finally:
            if client is not None:
                client.stop()

        if not diags:
            return ToolResult(success=True, output="No diagnostics found.")

        severity_labels = {1: "ERROR", 2: "WARNING", 3: "INFO", 4: "HINT"}
        lines = [f"LSP diagnostics for '{path.name}':"]
        for diag in diags:
            sev = diag.get("severity", 1)
            label = severity_labels.get(sev, "UNKNOWN")
            msg = diag.get("message", "")
            source = diag.get("source", "")
            rng = diag.get("range", {})
            start = rng.get("start", {})
            line = (start.get("line", 0) + 1) if start else 0
            col = (start.get("character", 0) + 1) if start else 0
            source_info = f" [{source}]" if source else ""
            lines.append(f"  Line {line}:{col} [{label}]{source_info}: {msg}")

        return ToolResult(success=True, output="\n".join(lines))
