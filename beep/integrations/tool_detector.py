"""External tool detector — detect CLI tools on PATH for agents and diagnostics."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class ToolStatus:
    tool_id: str
    found: bool
    path: str = ""
    version: str = ""
    install_hint: str = ""


def detect(tool_id: str) -> ToolStatus:
    tool_info = _TOOL_INFO.get(tool_id, {})
    command_name = tool_info.get("command", tool_id)
    version_flag = tool_info.get("version_flag", "--version")
    install_hint = tool_info.get("install_hint", "")

    exe_path = shutil.which(command_name)
    if exe_path is None:
        return ToolStatus(
            tool_id=tool_id,
            found=False,
            install_hint=install_hint,
        )

    version = ""
    try:
        result = subprocess.run(
            [command_name, version_flag],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = (result.stdout or result.stderr or "").strip()
        if output:
            version = output.split("\n")[0]
    except Exception:
        pass

    return ToolStatus(
        tool_id=tool_id,
        found=True,
        path=exe_path,
        version=version,
        install_hint=install_hint,
    )


def detect_all() -> list[ToolStatus]:
    return [detect(tool_id) for tool_id in _TOOL_INFO]


_TOOL_INFO: dict[str, dict[str, str]] = {
    "ripgrep": {
        "command": "rg",
        "version_flag": "--version",
        "install_hint": "cargo install ripgrep or use your system package manager",
    },
    "fd": {
        "command": "fd",
        "version_flag": "--version",
        "install_hint": "cargo install fd-find or use your system package manager",
    },
    "gh": {
        "command": "gh",
        "version_flag": "--version",
        "install_hint": "Install from https://cli.github.com",
    },
    "semgrep": {
        "command": "semgrep",
        "version_flag": "--version",
        "install_hint": "pip install semgrep",
    },
    "ruff": {
        "command": "ruff",
        "version_flag": "--version",
        "install_hint": "pip install ruff",
    },
    "mypy": {
        "command": "mypy",
        "version_flag": "--version",
        "install_hint": "pip install mypy",
    },
    "eslint": {
        "command": "eslint",
        "version_flag": "--version",
        "install_hint": "npm install -g eslint",
    },
    "prettier": {
        "command": "prettier",
        "version_flag": "--version",
        "install_hint": "npm install -g prettier",
    },
    "jq": {
        "command": "jq",
        "version_flag": "--version",
        "install_hint": "Install via your system package manager",
    },
    "docker": {
        "command": "docker",
        "version_flag": "--version",
        "install_hint": "Install from https://docs.docker.com/get-docker",
    },
    "node": {
        "command": "node",
        "version_flag": "--version",
        "install_hint": "Install from https://nodejs.org",
    },
    "git": {
        "command": "git",
        "version_flag": "--version",
        "install_hint": "Install via your system package manager",
    },
}
