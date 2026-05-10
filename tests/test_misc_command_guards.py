"""Tests for guardrails on non-async command entrypoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.exceptions import Exit

from beep.commands.analyze import analyze_cmd
from beep.commands.template import template_cmd, template_list_cmd


def test_analyze_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.commands.analyze.analyze_project", side_effect=RuntimeError("boom")):
        with pytest.raises(Exit):
            analyze_cmd(path=".")
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_template_cmd_handles_generation_error(capsys) -> None:
    class _Template:
        name = "x"

    with patch("beep.commands.template.find_workspace_root") as root_mock:
        root_mock.return_value = "."
        with patch("beep.commands.template.get_template_by_name", return_value=_Template()):
            with patch(
                    "beep.commands.template.generate_from_template",
                    side_effect=RuntimeError("boom"),
                ):
                with pytest.raises(Exit):
                    template_cmd(name="x", output="out.txt", var=None)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()


def test_template_list_cmd_handles_runtime_error(capsys) -> None:
    with patch("beep.commands.template.find_workspace_root") as root_mock:
        root_mock.return_value = "."
        with patch("beep.commands.template.list_templates", side_effect=RuntimeError("boom")):
            with pytest.raises(Exit):
                template_list_cmd(category=None)
    out = capsys.readouterr().out
    assert "error: boom" in out.lower()
