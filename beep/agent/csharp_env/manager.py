"""Environment manager for the C# Roslyn analyzer tool and .NET SDK."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from beep.config import CONFIG_DIR

ProgressCallback = Callable[[str, int, str], None]

_DOTNET_MIN_VERSION = "8.0"
_ANALYZER_PROJECT_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "tools"
    / "Beep.CSharpAnalyzer"
    / "Beep.CSharpAnalyzer"
)
_CONFIG_FILE = CONFIG_DIR / "csharp_analyzer_config.json"


class DotNetSDKInfo:
    """Information about the installed .NET SDK."""

    def __init__(self, installed: bool = False, version: str = "", sdk_path: str = ""):
        self.installed = installed
        self.version = version
        self.sdk_path = sdk_path
        self.meets_minimum = self._check_minimum()

    def _check_minimum(self) -> bool:
        if not self.version:
            return False
        try:
            major = int(self.version.split(".")[0])
            return major >= int(_DOTNET_MIN_VERSION.split(".")[0])
        except (ValueError, IndexError):
            return False


def check_dotnet_sdk() -> DotNetSDKInfo:
    """Check if .NET SDK is installed and meets minimum version."""
    try:
        result = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            sdk_path_result = subprocess.run(
                ["dotnet", "--list-sdks"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            sdk_path = ""
            if sdk_path_result.returncode == 0 and sdk_path_result.stdout:
                lines = sdk_path_result.stdout.strip().splitlines()
                if lines:
                    parts = lines[0].split("[")
                    if len(parts) > 1:
                        sdk_path = parts[-1].rstrip("]").strip()
            return DotNetSDKInfo(installed=True, version=version, sdk_path=sdk_path)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return DotNetSDKInfo()


def check_roslyn_analyzer() -> dict[str, Any]:
    """Check if the Roslyn analyzer project exists and is buildable."""
    csproj = _ANALYZER_PROJECT_DIR / "Beep.CSharpAnalyzer.csproj"
    return {
        "project_dir": str(_ANALYZER_PROJECT_DIR),
        "csproj_exists": csproj.exists(),
        "program_cs_exists": (_ANALYZER_PROJECT_DIR / "Program.cs").exists(),
        "built": (_ANALYZER_PROJECT_DIR / "bin" / "Debug").exists(),
    }


def build_roslyn_analyzer(progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    """Restore and build the Roslyn analyzer project."""
    if progress_callback:
        progress_callback("Restoring NuGet packages...", 10, "restore")

    try:
        restore = subprocess.run(
            ["dotnet", "restore", str(_ANALYZER_PROJECT_DIR)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if restore.returncode != 0:
            return {
                "ok": False,
                "error": f"dotnet restore failed: {restore.stderr or restore.stdout}",
            }

        if progress_callback:
            progress_callback("Building analyzer...", 60, "build")

        build = subprocess.run(
            ["dotnet", "build", str(_ANALYZER_PROJECT_DIR), "--no-restore"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if build.returncode != 0:
            return {
                "ok": False,
                "error": f"dotnet build failed: {build.stderr or build.stdout}",
            }

        if progress_callback:
            progress_callback("Build complete.", 100, "done")

        return {"ok": True}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Build timed out after 300s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def is_ready() -> bool:
    """Return True when .NET SDK and the Roslyn analyzer are both ready."""
    sdk = check_dotnet_sdk()
    analyzer = check_roslyn_analyzer()
    return sdk.installed and sdk.meets_minimum and analyzer["csproj_exists"] and analyzer["built"]


def status() -> dict[str, Any]:
    """Return full status of the C# analysis environment."""
    sdk = check_dotnet_sdk()
    analyzer = check_roslyn_analyzer()

    sdk_ok = sdk.installed and sdk.meets_minimum
    analyzer_ok = analyzer["csproj_exists"] and analyzer["built"]
    ready = sdk_ok and analyzer_ok

    if not sdk_ok:
        status_label = "dotnet_sdk_missing" if not sdk.installed else "dotnet_sdk_outdated"
    elif not analyzer["csproj_exists"]:
        status_label = "analyzer_project_missing"
    elif not analyzer["built"]:
        status_label = "analyzer_not_built"
    else:
        status_label = "ready"

    return {
        "status": status_label,
        "ready": ready,
        "dotnet_sdk": {
            "installed": sdk.installed,
            "version": sdk.version,
            "sdk_path": sdk.sdk_path,
            "meets_minimum": sdk.meets_minimum,
            "minimum_required": _DOTNET_MIN_VERSION,
        },
        "roslyn_analyzer": analyzer,
        "actions": _compute_actions(sdk_ok, analyzer),
    }


def _compute_actions(sdk_ok: bool, analyzer: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if not sdk_ok:
        actions.append("Install .NET SDK 8.0+ from https://dotnet.microsoft.com/download")
    if not analyzer["csproj_exists"]:
        actions.append("Roslyn analyzer project not found — reinstall beep or run setup")
    elif not analyzer["built"]:
        actions.append("Run 'beep csharp setup' or 'beep csharp build' to build the analyzer")
    return actions


def _load_config() -> dict[str, Any]:
    if not _CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_config(payload: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
