"""Managed Python environment for the LangGraph-based agent runtime."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, ClassVar

from beep import __version__
from beep.agent.environment_catalog import AGENT_PACKAGES, AgentPackage
from beep.agent import environment_runtime_support
from beep.agent.environment_policy import (
    build_compatibility_stamp,
    resolve_compatibility,
    resolve_repair_guidance,
)
from beep.config import CONFIG_DIR

ProgressCallback = Callable[[str, int, str], None]


class AgentEnvironmentManager:
    """Manage the dedicated on-demand virtual environment for agent orchestration."""

    _COMPATIBILITY_METADATA_VERSION: ClassVar[int] = 1
    _instances: ClassVar[dict[str, "AgentEnvironmentManager"]] = {}

    def __new__(cls, base_dir: Path | None = None) -> "AgentEnvironmentManager":
        resolved = (base_dir or CONFIG_DIR).expanduser().resolve()
        key = str(resolved)
        instance = cls._instances.get(key)
        if instance is None:
            instance = super().__new__(cls)
            cls._instances[key] = instance
            instance._initialized = False
        return instance

    def __init__(self, base_dir: Path | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._base_dir = (base_dir or CONFIG_DIR).expanduser().resolve()
        self._env_path = self._base_dir / "agents_env"
        self._config_file = self._base_dir / "agents_env_config.json"

    def python_exe(self) -> Path:
        """Return the Python executable inside the managed environment."""
        if os.name == "nt":
            return self._env_path / "Scripts" / "python.exe"
        return self._env_path / "bin" / "python"

    def site_packages(self) -> Path:
        """Resolve the site-packages folder inside the managed environment."""
        return environment_runtime_support.site_packages(self)

    def inject_into_sys_path(self) -> Path:
        """Make the managed environment importable from the current process."""
        return environment_runtime_support.inject_into_sys_path(self)

    def is_ready(self) -> bool:
        """Return True when the environment and all required packages are present."""
        return environment_runtime_support.is_ready(self)

    def status(self) -> dict[str, Any]:
        """Return computed status for the managed environment."""
        return environment_runtime_support.status(self)

    def create_environment(self, progress_callback: ProgressCallback | None = None) -> Path:
        """Create the managed virtual environment if needed."""
        return environment_runtime_support.create_environment(self, progress_callback=progress_callback)

    def install_required_packages(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Install all required LangGraph runtime packages into the managed environment."""
        return environment_runtime_support.install_required_packages(
            self,
            progress_callback=progress_callback,
        )

    def reinstall_package(
        self,
        package_name: str,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Reinstall one package in the managed environment."""
        return environment_runtime_support.reinstall_package(
            self,
            package_name,
            progress_callback=progress_callback,
        )

    def reinstall_environment(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Rebuild the entire managed runtime environment from scratch."""
        return environment_runtime_support.reinstall_environment(
            self,
            progress_callback=progress_callback,
        )

    def uninstall_environment(self) -> None:
        """Remove the managed environment and its persisted status."""
        environment_runtime_support.uninstall_environment(self)

    def _install_package(
        self,
        package: AgentPackage,
        *,
        upgrade: bool,
        force_reinstall: bool = False,
    ) -> None:
        command = [str(self.python_exe()), "-m", "pip", "install"]
        if upgrade:
            command.append("--upgrade")
        if force_reinstall:
            command.append("--force-reinstall")
        command.append(package.pip_name)
        self._run_subprocess(command, timeout=1200)

    def _resolve_package(self, package_name: str) -> AgentPackage:
        normalized = package_name.strip().lower()
        for package in AGENT_PACKAGES.values():
            if normalized in {
                package.key.lower(),
                package.name.lower(),
                package.import_name.lower(),
                package.pip_name.lower(),
            }:
                return package
        valid = ", ".join(sorted(AGENT_PACKAGES))
        raise ValueError(f"Unknown agent package '{package_name}'. Choose one of: {valid}")

    def _probe_import_available(self, import_name: str) -> bool:
        python_exe = self.python_exe()
        if not python_exe.exists():
            return False
        result = subprocess.run(
            [
                str(python_exe),
                "-c",
                (
                    "import importlib.util, sys; "
                    "sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)"
                ),
                import_name,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0

    def _run_subprocess(self, command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            error = (result.stderr or result.stdout or "unknown error").strip()
            raise RuntimeError(error)
        return result

    def _load_config(self) -> dict[str, Any]:
        if not self._config_file.exists():
            return {}
        try:
            return json.loads(self._config_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_config(
        self,
        *,
        status: str,
        last_error: str | None,
        compatibility: dict[str, Any] | None = None,
    ) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        existing = self._load_config()
        payload = {
            "status": status,
            "env_path": str(self._env_path),
            "python_exe": str(self.python_exe()),
            "last_error": last_error,
        }
        recorded_compatibility = compatibility if compatibility is not None else existing.get("compatibility")
        if isinstance(recorded_compatibility, dict):
            payload["compatibility"] = recorded_compatibility
        self._config_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _build_compatibility_stamp(self) -> dict[str, Any]:
        return build_compatibility_stamp(
            packages=AGENT_PACKAGES,
            cli_version=__version__,
            metadata_version=self._COMPATIBILITY_METADATA_VERSION,
        )

    def _resolve_compatibility(
        self,
        config: dict[str, Any],
        *,
        env_exists: bool,
        missing: list[str],
    ) -> dict[str, Any]:
        return resolve_compatibility(
            config=config,
            env_exists=env_exists,
            missing=missing,
            expected=self._build_compatibility_stamp(),
        )

    def _resolve_repair_guidance(
        self,
        *,
        config: dict[str, Any],
        status: str,
        compatibility: dict[str, Any],
        missing: list[str],
    ) -> dict[str, Any]:
        return resolve_repair_guidance(
            config=config,
            status=status,
            compatibility=compatibility,
            missing=missing,
        )

    def _directory_size(self, root: Path) -> int:
        total = 0
        if not root.exists():
            return total
        for path in root.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total