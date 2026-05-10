from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.exceptions import Exit

from beep.commands.self_update import (
    SelfUpdatePlan,
    UpdateStep,
    detect_self_update_plan,
    self_update_cmd,
)


class _FakeDistribution:
    def __init__(self, direct_url: dict[str, object] | None) -> None:
        self._direct_url = direct_url

    def read_text(self, name: str) -> str | None:
        if name != "direct_url.json" or self._direct_url is None:
            return None
        return json.dumps(self._direct_url)


def test_detect_self_update_plan_prefers_pipx_channel() -> None:
    with patch("beep.commands.self_update._running_in_pipx_environment", return_value=True):
        plan = detect_self_update_plan()

    assert plan.channel == "pipx"
    assert plan.can_execute is True
    assert plan.steps[0].command == ("pipx", "upgrade", "beep-ai-code")


def test_detect_self_update_plan_for_editable_checkout() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        distribution = _FakeDistribution(
            {
                "url": root.as_uri(),
                "dir_info": {"editable": True},
            }
        )
        with patch("beep.commands.self_update._running_in_pipx_environment", return_value=False):
            with patch("beep.commands.self_update._read_distribution", return_value=distribution):
                plan = detect_self_update_plan()

    assert plan.channel == "editable"
    assert plan.can_execute is True
    assert plan.steps[0].command == ("git", "pull", "--ff-only")
    assert plan.steps[0].cwd == root
    assert plan.steps[1].cwd == root
    assert plan.steps[1].command[:4] == (pytest.sys.executable if False else plan.steps[1].command[0], "-m", "pip", "install")
    assert plan.steps[1].command[-2:] == ("-e", ".[dev]")


def test_detect_self_update_plan_for_index_install() -> None:
    distribution = _FakeDistribution(None)
    with patch("beep.commands.self_update._running_in_pipx_environment", return_value=False):
        with patch("beep.commands.self_update._read_distribution", return_value=distribution):
            plan = detect_self_update_plan()

    assert plan.channel == "index"
    assert plan.can_execute is True
    assert plan.steps[0].command[-1] == "beep-ai-code"


def test_detect_self_update_plan_for_local_artifact_requires_manual_reinstall() -> None:
    with tempfile.TemporaryDirectory() as td:
        artifact = Path(td) / "beep_ai_code-0.1.0.whl"
        artifact.write_text("wheel", encoding="utf-8")
        distribution = _FakeDistribution(
            {
                "url": artifact.as_uri(),
                "archive_info": {"hash": "sha256=abc"},
            }
        )
        with patch("beep.commands.self_update._running_in_pipx_environment", return_value=False):
            with patch("beep.commands.self_update._read_distribution", return_value=distribution):
                plan = detect_self_update_plan()

    assert plan.channel == "local-artifact"
    assert plan.can_execute is False
    assert plan.steps == ()


def test_self_update_cmd_dry_run_prints_plan(capsys) -> None:
    plan = SelfUpdatePlan(
        channel="index",
        summary="summary",
        note="note",
        can_execute=True,
        steps=(UpdateStep(command=("python", "-m", "pip"), display="python -m pip"),),
    )
    with patch("beep.commands.self_update.detect_self_update_plan", return_value=plan):
        self_update_cmd(yes=False)

    out = capsis = capsys.readouterr().out
    assert "Self Update Plan" in out
    assert "Dry run only" in out


def test_self_update_cmd_executes_when_yes() -> None:
    plan = SelfUpdatePlan(
        channel="index",
        summary="summary",
        note=None,
        can_execute=True,
        steps=(UpdateStep(command=("python", "-m", "pip"), display="python -m pip"),),
    )
    with patch("beep.commands.self_update.detect_self_update_plan", return_value=plan):
        with patch("beep.commands.self_update._run_step") as run_step:
            self_update_cmd(yes=True)

    run_step.assert_called_once_with(plan.steps[0])


def test_self_update_cmd_rejects_manual_only_channel() -> None:
    plan = SelfUpdatePlan(
        channel="local-artifact",
        summary="summary",
        note="manual reinstall required",
        can_execute=False,
        steps=(),
    )
    with patch("beep.commands.self_update.detect_self_update_plan", return_value=plan):
        with pytest.raises(Exit):
            self_update_cmd(yes=True)