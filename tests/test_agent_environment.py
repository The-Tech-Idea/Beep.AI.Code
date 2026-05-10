"""Tests for the managed LangGraph agent environment."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from beep.agent.environment import AgentEnvironmentManager


def _manager(base_dir: Path) -> AgentEnvironmentManager:
    AgentEnvironmentManager._instances.pop(str(base_dir.resolve()), None)
    return AgentEnvironmentManager(base_dir=base_dir)


def test_status_reports_not_created_when_env_missing() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        status = manager.status()
        assert status["status"] == "not_created"
        assert status["compatibility_status"] == "not_created"
        assert status["repair_action"] == "setup"
        assert status["repair_command"] == "beep agent setup"
        assert Path(str(status["env_path"])) == Path(td) / "agents_env"
        assert "langgraph" in status["missing"]


def test_create_environment_reuses_existing_python() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        env_path = manager.create_environment()
        assert env_path == Path(td) / "agents_env"
        assert manager.python_exe().exists()


def test_install_required_packages_invokes_pip_for_required_packages() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        commands: list[list[str]] = []

        def fake_run(command: list[str], *, timeout: int):
            commands.append(command)

            class Result:
                stdout = ""

            return Result()

        with patch.object(manager, "_run_subprocess", side_effect=fake_run):
            with patch.object(manager, "_probe_import_available", return_value=True):
                status = manager.install_required_packages()

        assert status["status"] == "ready"
        assert status["compatibility_status"] == "current"
        assert any("--upgrade" in command and "pip" in command for command in commands)
        required_installs = [command[-1] for command in commands if "install" in command and command[-1] != "pip"]
        assert set(required_installs) >= {
            "langgraph>=0.4",
            "langchain-core>=0.3",
            "langgraph-checkpoint-sqlite>=2.0",
            "pydantic>=2.0",
            "semble>=0.1.1",
            "jedi>=0.19",
        }
        persisted = manager._load_config()
        assert persisted["compatibility"]["cli_version"]
        assert persisted["compatibility"]["catalog_hash"]


def test_install_required_packages_preserves_current_runtime() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        manager._write_config(
            status="ready",
            last_error=None,
            compatibility=manager._build_compatibility_stamp(),
        )

        with patch.object(manager, "_probe_import_available", return_value=True):
            with patch.object(manager, "_run_subprocess") as run_subprocess:
                status = manager.install_required_packages()

        assert status["status"] == "ready"
        assert status["compatibility_status"] == "current"
        run_subprocess.assert_not_called()


def test_install_required_packages_refreshes_stale_runtime() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        manager._write_config(
            status="ready",
            last_error=None,
            compatibility=manager._build_compatibility_stamp() | {"cli_version": "0.0.0"},
        )
        commands: list[list[str]] = []

        def fake_run(command: list[str], *, timeout: int):
            commands.append(command)

            class Result:
                stdout = ""

            return Result()

        with patch.object(manager, "_run_subprocess", side_effect=fake_run):
            with patch.object(manager, "_probe_import_available", return_value=True):
                status = manager.install_required_packages()

        assert status["status"] == "ready"
        assert status["compatibility_status"] == "current"
        assert commands


def test_status_recommends_runtime_reinstall_after_interrupted_setup() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        manager._write_config(status="creating", last_error="pip install interrupted")

        with patch.object(manager, "_probe_import_available", return_value=False):
            status = manager.status()

        assert status["status"] == "error"
        assert status["repair_action"] == "reinstall"
        assert status["repair_command"] == "beep agent reinstall runtime"
        assert "did not complete cleanly" in str(status["repair_reason"])


def test_install_required_packages_rejects_interrupted_runtime_until_reinstall() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        manager._write_config(status="creating", last_error="pip install interrupted")

        with patch.object(manager, "_probe_import_available", return_value=False):
            with patch.object(manager, "_run_subprocess") as run_subprocess:
                with patch.object(manager, "create_environment") as create_environment:
                    try:
                        manager.install_required_packages()
                    except RuntimeError as exc:
                        assert "beep agent reinstall runtime" in str(exc)
                    else:
                        raise AssertionError("expected RuntimeError")

        create_environment.assert_not_called()
        run_subprocess.assert_not_called()


def test_status_reports_stale_when_runtime_stamp_mismatches() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        stale = manager._build_compatibility_stamp() | {"cli_version": "0.0.0"}
        manager._write_config(status="ready", last_error=None, compatibility=stale)

        with patch.object(manager, "_probe_import_available", return_value=True):
            status = manager.status()

        assert status["status"] == "ready"
        assert status["compatibility_status"] == "stale"
        assert status["repair_action"] == "setup"
        assert status["repair_command"] == "beep agent setup"
        assert "cli_version" in str(status["compatibility_reason"])


def test_status_recommends_runtime_reinstall_when_metadata_version_changes() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        python_exe = manager.python_exe()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("", encoding="utf-8")
        stale = manager._build_compatibility_stamp() | {"metadata_version": 0}
        manager._write_config(status="ready", last_error=None, compatibility=stale)

        with patch.object(manager, "_probe_import_available", return_value=True):
            status = manager.status()

        assert status["compatibility_status"] == "stale"
        assert status["repair_action"] == "reinstall"
        assert status["repair_command"] == "beep agent reinstall runtime"


def test_reinstall_environment_rebuilds_from_scratch() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        expected = {"status": "ready", "compatibility_status": "current"}

        with patch.object(manager, "uninstall_environment") as uninstall_environment:
            with patch.object(manager, "install_required_packages", return_value=expected) as install_required_packages:
                status = manager.reinstall_environment()

        uninstall_environment.assert_called_once_with()
        install_required_packages.assert_called_once_with(progress_callback=None)
        assert status is expected


def test_inject_into_sys_path_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as td:
        manager = _manager(Path(td))
        site_packages = Path(td) / "agents_env" / "Lib" / "site-packages"
        site_packages.mkdir(parents=True, exist_ok=True)
        original = list(sys.path)
        try:
            manager.inject_into_sys_path()
            manager.inject_into_sys_path()
            normalized = [entry.casefold() for entry in sys.path]
            assert normalized.count(str(site_packages).casefold()) == 1
        finally:
            sys.path[:] = original