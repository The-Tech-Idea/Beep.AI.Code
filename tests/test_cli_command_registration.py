"""Tests for lazy CLI command forwarding wrappers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from beep.cli_command_registration import doctor_command, tree_command


def test_tree_command_dispatches_to_workspace_module() -> None:
    module = MagicMock()

    with patch("beep.cli_command_registration.import_module", return_value=module) as import_mock:
        tree_command(path="src", depth=4, all_files=True)

    import_mock.assert_called_once_with("beep.commands.workspace")
    module.tree_cmd.assert_called_once_with("src", 4, True)


def test_doctor_command_dispatches_keyword_arguments() -> None:
    module = MagicMock()

    with patch("beep.cli_command_registration.import_module", return_value=module) as import_mock:
        doctor_command(fix=True)

    import_mock.assert_called_once_with("beep.commands.diagnostics")
    module.doctor_cmd.assert_called_once_with(fix=True)