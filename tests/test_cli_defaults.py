"""Tests for default CLI invocation parsing."""

from beep.cli_defaults import parse_default_invocation

SUBCOMMANDS = {"chat", "setup", "ask"}


def test_parse_default_question_ignores_flag_values() -> None:
    invocation = parse_default_invocation(
        ["--model", "model-a", "hello", "world", "--mode", "review"],
        SUBCOMMANDS,
    )

    assert invocation.kind == "ask"
    assert invocation.question == "hello world"
    assert invocation.model == "model-a"
    assert invocation.mode == "review"


def test_parse_default_chat_flags() -> None:
    invocation = parse_default_invocation(
        ["--model", "model-a", "--resume", "s-1", "--tokens", "--no-plugins"],
        SUBCOMMANDS,
    )

    assert invocation.kind == "chat"
    assert invocation.model == "model-a"
    assert invocation.resume == "s-1"
    assert invocation.tokens is True
    assert invocation.no_plugins is True
