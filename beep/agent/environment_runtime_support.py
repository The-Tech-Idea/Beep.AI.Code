"""Runtime orchestration helpers for the managed agent environment."""

from __future__ import annotations

import importlib
import shutil
import sys
from typing import TYPE_CHECKING, Any

from beep.agent.environment_catalog import AGENT_PACKAGES

if TYPE_CHECKING:
    from pathlib import Path

    from beep.agent.environment import AgentEnvironmentManager, ProgressCallback


def site_packages(manager: AgentEnvironmentManager) -> Path:
    candidates = [
        manager._env_path / "Lib" / "site-packages",
        manager._env_path
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    python_exe = manager.python_exe()
    if not python_exe.exists():
        raise RuntimeError(
            f"Agent environment not created at {manager._env_path}. Run `beep agent setup`."
        )

    result = manager._run_subprocess(
        [
            str(python_exe),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        timeout=30,
    )
    site_packages_path = Path(result.stdout.strip())
    if not site_packages_path.exists():
        raise RuntimeError(f"Unable to locate site-packages in {manager._env_path}.")
    return site_packages_path


def inject_into_sys_path(manager: AgentEnvironmentManager) -> Path:
    site_packages_path = manager.site_packages()
    site_packages_str = str(site_packages_path)
    if site_packages_str not in sys.path:
        sys.path.insert(0, site_packages_str)
        importlib.invalidate_caches()
    return site_packages_path


def is_ready(manager: AgentEnvironmentManager) -> bool:
    return manager.status()["status"] == "ready"


def status(manager: AgentEnvironmentManager) -> dict[str, Any]:
    config = manager._load_config()
    env_exists = manager.python_exe().exists()
    packages: dict[str, dict[str, Any]] = {}
    missing: list[str] = []

    if env_exists:
        for key, package in AGENT_PACKAGES.items():
            installed = manager._probe_import_available(package.import_name)
            packages[key] = {
                "name": package.name,
                "pip_name": package.pip_name,
                "import_name": package.import_name,
                "description": package.description,
                "required": package.required,
                "installed": installed,
            }
            if package.required and not installed:
                missing.append(key)
    else:
        for key, package in AGENT_PACKAGES.items():
            packages[key] = {
                "name": package.name,
                "pip_name": package.pip_name,
                "import_name": package.import_name,
                "description": package.description,
                "required": package.required,
                "installed": False,
            }
            if package.required:
                missing.append(key)

    if not env_exists:
        current_status = "not_created"
    elif missing:
        current_status = "error"
    else:
        current_status = "ready"

    compatibility = manager._resolve_compatibility(config, env_exists=env_exists, missing=missing)
    repair = manager._resolve_repair_guidance(
        config=config,
        status=current_status,
        compatibility=compatibility,
        missing=missing,
    )

    return {
        "status": current_status,
        "env_path": str(manager._env_path),
        "python_exe": str(manager.python_exe()),
        "config_file": str(manager._config_file),
        "missing": missing,
        "packages": packages,
        "size_bytes": manager._directory_size(manager._env_path) if env_exists else 0,
        "last_error": config.get("last_error"),
        "compatibility_status": compatibility["status"],
        "compatibility_reason": compatibility["reason"],
        "recorded_compatibility": compatibility["recorded"],
        "expected_compatibility": compatibility["expected"],
        "repair_action": repair["action"],
        "repair_command": repair["command"],
        "repair_reason": repair["reason"],
    }


def create_environment(
    manager: AgentEnvironmentManager,
    progress_callback: ProgressCallback | None = None,
) -> Path:
    manager._base_dir.mkdir(parents=True, exist_ok=True)
    if manager.python_exe().exists():
        if progress_callback:
            progress_callback("creating", 30, "Using existing agent environment")
        return manager._env_path

    manager._write_config(status="creating", last_error=None)
    if progress_callback:
        progress_callback("creating", 5, "Creating managed agent environment")
    try:
        manager._run_subprocess([sys.executable, "-m", "venv", str(manager._env_path)], timeout=300)
    except Exception as exc:
        manager._write_config(status="error", last_error=str(exc))
        raise

    if progress_callback:
        progress_callback("creating", 30, f"Created environment at {manager._env_path}")
    manager._write_config(status="creating", last_error=None)
    return manager._env_path


def install_required_packages(
    manager: AgentEnvironmentManager,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    current_status = manager.status()
    if (
        current_status.get("status") == "ready"
        and current_status.get("compatibility_status") == "current"
    ):
        if progress_callback:
            progress_callback("ready", 100, "Managed agent environment already current")
        manager._write_config(
            status="ready",
            last_error=None,
            compatibility=manager._build_compatibility_stamp(),
        )
        return current_status
    if current_status.get("repair_action") == "reinstall":
        reason = str(
            current_status.get("repair_reason")
            or "Managed agent runtime requires a full rebuild."
        )
        command = str(current_status.get("repair_command") or "beep agent reinstall runtime")
        raise RuntimeError(f'{reason} Run "{command}".')

    manager.create_environment(progress_callback=progress_callback)
    python_exe = manager.python_exe()

    if progress_callback:
        progress_callback("pip", 35, "Upgrading pip")
    manager._write_config(status="creating", last_error=None)
    try:
        manager._run_subprocess(
            [
                str(python_exe),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
            ],
            timeout=240,
        )

        required_packages = [package for package in AGENT_PACKAGES.values() if package.required]
        for index, package in enumerate(required_packages, start=1):
            if progress_callback:
                pct = 35 + int((index - 1) * 60 / max(len(required_packages), 1))
                progress_callback(
                    "installing",
                    pct,
                    f"Installing {package.pip_name} ({index}/{len(required_packages)})",
                )
            manager._install_package(package, upgrade=True)
    except Exception as exc:
        manager._write_config(status="error", last_error=str(exc))
        raise

    resolved_status = manager.status()
    if resolved_status["missing"]:
        error_message = (
            "Managed agent environment is incomplete; missing required packages: "
            + ", ".join(resolved_status["missing"])
        )
        manager._write_config(status="error", last_error=error_message)
        raise RuntimeError(error_message)

    manager._write_config(
        status="ready",
        last_error=None,
        compatibility=manager._build_compatibility_stamp(),
    )
    resolved_status = manager.status()
    if progress_callback:
        progress_callback("ready", 100, "Agent environment is ready")
    return resolved_status


def reinstall_package(
    manager: AgentEnvironmentManager,
    package_name: str,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    manager.create_environment(progress_callback=progress_callback)
    package = manager._resolve_package(package_name)
    if progress_callback:
        progress_callback("installing", 40, f"Reinstalling {package.pip_name}")
    manager._install_package(package, upgrade=True, force_reinstall=True)
    current_status = manager.status()
    manager._write_config(
        status=current_status["status"],
        last_error=None,
        compatibility=(
            manager._build_compatibility_stamp() if current_status["status"] == "ready" else None
        ),
    )
    if progress_callback:
        progress_callback("ready", 100, f"Reinstalled {package.pip_name}")
    return current_status


def reinstall_environment(
    manager: AgentEnvironmentManager,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    if progress_callback:
        progress_callback("reinstalling", 5, "Removing managed agent environment")
    manager.uninstall_environment()
    if progress_callback:
        progress_callback("reinstalling", 15, "Recreating managed agent environment")
    return manager.install_required_packages(progress_callback=progress_callback)


def uninstall_environment(manager: AgentEnvironmentManager) -> None:
    if manager._env_path.exists():
        shutil.rmtree(manager._env_path)
    if manager._config_file.exists():
        manager._config_file.unlink()