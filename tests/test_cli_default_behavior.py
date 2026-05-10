"""Tests for default CLI dispatch behavior."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from beep import cli


def test_run_default_passes_multi_word_question() -> None:
    with patch("sys.argv", ["beep", "hello", "world"]):
        with patch("beep.commands.ask.ask_cmd") as ask_mock:
            cli._run_default()
    ask_mock.assert_called_once()
    args, kwargs = ask_mock.call_args
    assert args[0] == "hello world"
    assert kwargs["model"] is None


def test_run_default_question_ignores_model_flag_value() -> None:
    with patch("sys.argv", ["beep", "hello", "world", "--model", "gpt-test"]):
        with patch("beep.commands.ask.ask_cmd") as ask_mock:
            cli._run_default()
    ask_mock.assert_called_once()
    args, kwargs = ask_mock.call_args
    assert args[0] == "hello world"
    assert kwargs["model"] == "gpt-test"


def test_run_default_parses_question_when_flags_come_first() -> None:
    with patch("sys.argv", ["beep", "--model", "gpt-test", "hello", "world"]):
        with patch("beep.commands.ask.ask_cmd") as ask_mock:
            cli._run_default()
    ask_mock.assert_called_once()
    args, kwargs = ask_mock.call_args
    assert args[0] == "hello world"
    assert kwargs["model"] == "gpt-test"


def test_run_default_passes_mode_to_one_shot_question() -> None:
    with patch("sys.argv", ["beep", "hello", "world", "--mode", "review"]):
        with patch("beep.commands.ask.ask_cmd") as ask_mock:
            cli._run_default()
    ask_mock.assert_called_once()
    args, kwargs = ask_mock.call_args
    assert args[0] == "hello world"
    assert kwargs["mode"] == "review"


def test_is_subcommand_only_checks_first_arg() -> None:
    with patch("sys.argv", ["beep", "hello", "setup"]):
        assert cli._is_subcommand() is False


def test_is_subcommand_true_for_first_arg_subcommand() -> None:
    with patch("sys.argv", ["beep", "setup"]):
        assert cli._is_subcommand() is True


def test_is_subcommand_true_for_explicit_named_core_command() -> None:
    with patch("sys.argv", ["beep", "config-set"]):
        assert cli._is_subcommand() is True


@pytest.mark.parametrize("token", ["watch", "template", "rag"])
def test_is_subcommand_true_for_registered_command_tokens(token: str) -> None:
    with patch("sys.argv", ["beep", token]):
        assert cli._is_subcommand() is True


def test_is_subcommand_true_for_leading_unknown_flag() -> None:
    with patch("sys.argv", ["beep", "--unknown-flag"]):
        assert cli._is_subcommand() is True
