"""Default invocation parsing for the Beep.AI.Code CLI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefaultInvocation:
    """Parsed commandless CLI invocation."""

    kind: str
    question: str = ""
    model: str | None = None
    mode: str = "assistant"
    resume: str | None = None
    tokens: bool = False
    no_plugins: bool = False


def parse_default_invocation(args: list[str], subcommands: set[str]) -> DefaultInvocation:
    """Parse `beep` and `beep "question"` fallback behavior."""
    values = _parse_flag_values(args)
    question_parts = _non_flag_args(args)
    if question_parts and question_parts[0] not in subcommands:
        return DefaultInvocation(
            kind="ask",
            question=" ".join(question_parts).strip(),
            model=values.model,
            mode=values.mode,
        )
    return DefaultInvocation(
        kind="chat",
        model=values.model,
        mode=values.mode,
        resume=values.resume,
        tokens=values.tokens,
        no_plugins=values.no_plugins,
    )


@dataclass(frozen=True)
class _FlagValues:
    model: str | None = None
    mode: str = "assistant"
    resume: str | None = None
    tokens: bool = False
    no_plugins: bool = False


def _parse_flag_values(args: list[str]) -> _FlagValues:
    model = None
    mode = "assistant"
    resume = None
    tokens = False
    no_plugins = False
    for index, arg in enumerate(args):
        if arg in ("-m", "--model") and index + 1 < len(args):
            model = args[index + 1]
        elif arg == "--mode" and index + 1 < len(args):
            mode = args[index + 1]
        elif arg in ("-r", "--resume") and index + 1 < len(args):
            resume = args[index + 1]
        elif arg == "--tokens":
            tokens = True
        elif arg == "--no-plugins":
            no_plugins = True
    return _FlagValues(
        model=model,
        mode=mode,
        resume=resume,
        tokens=tokens,
        no_plugins=no_plugins,
    )


def _non_flag_args(args: list[str]) -> list[str]:
    flags_with_values = {"-m", "--model", "--mode", "-r", "--resume"}
    filtered: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in flags_with_values:
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        filtered.append(arg)
        index += 1
    return filtered
