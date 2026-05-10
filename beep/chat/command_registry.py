"""Slash command registry for the interactive chat session."""

from __future__ import annotations

from beep.chat.commands.agent import AgentCommand
from beep.chat.commands.base import Command, CustomCommand
from beep.chat.commands.code import (
    AddCommand,
    CatCommand,
    EditCommand,
    GrepCommand,
    RemoveCommand,
    TreeCommand,
)
from beep.chat.commands.context import ContextCommand
from beep.chat.commands.coding import CodingCommand
from beep.chat.commands.llm_turns import AskCommand
from beep.chat.commands.mcp import McpCommand
from beep.chat.commands.memory import MemoryReloadCommand
from beep.chat.commands.misc import (
    ClipboardCommand,
    ExitCommand,
    HelpCommand,
    HooksCommand,
    ImageCommand,
    ImportCommand,
    InstallCommand,
    MaxTokensCommand,
    PluginsCommand,
    QuitCommand,
    RetryCommand,
    RulesCommand,
    SandboxCommand,
    SkillCommand,
    SkillsCommand,
    SummaryCommand,
)
from beep.chat.commands.model import (
    CostCommand,
    ModeCommand,
    ModelCommand,
    PermissionsCommand,
    TokensCommand,
)
from beep.chat.commands.productivity import (
    BookmarkCommand,
    FetchCommand,
    PickCommand,
    RunCodeCommand,
    ScanCommand,
    SearchCommand,
    TaskCommand,
)
from beep.chat.commands.quality import (
    AnalyzeCommand,
    LintCommand,
    ReviewCommand,
    TestCommand,
)
from beep.chat.commands.search import CollectionsCommand, RagCommand
from beep.chat.commands.session import (
    ClearCommand,
    CompactCommand,
    ResumeCommand,
    SessionCommand,
    SessionsCommand,
    UndoCommand,
)
from beep.chat.commands.system import (
    ConfigCommand,
    DiagnosticsCommand,
    StatusCommand,
    TemplatesCommand,
)
from beep.chat.commands.token import TokenCommand
from beep.chat.commands.watch import WatchCommand
from beep.chat.commands.workflow import (
    BashCommand,
    BranchCommand,
    CommitCommand,
    DiffCommand,
    OutputCommand,
    PRCommand,
    RevertCommand,
)


def build_command_registry() -> dict[str, Command]:
    """Register all first-party slash commands."""
    commands: list[Command] = [
        HelpCommand(),
        QuitCommand(),
        ExitCommand(),
        ClearCommand(),
        CompactCommand(),
        ResumeCommand(),
        SessionCommand(),
        SessionsCommand(),
        ModelCommand(),
        ModeCommand(),
        TokensCommand(),
        CostCommand(),
        PermissionsCommand(),
        AgentCommand(),
        CodingCommand(),
        CatCommand(),
        TreeCommand(),
        GrepCommand(),
        EditCommand(),
        AddCommand(),
        RemoveCommand(),
        BashCommand(),
        DiffCommand(),
        CommitCommand(),
        BranchCommand(),
        PRCommand(),
        UndoCommand(),
        RevertCommand(),
        OutputCommand(),
        ReviewCommand(),
        TestCommand(),
        LintCommand(),
        AnalyzeCommand(),
        RagCommand(),
        CollectionsCommand(),
        StatusCommand(),
        ConfigCommand(),
        DiagnosticsCommand(),
        TemplatesCommand(),
        TokenCommand(),
        RetryCommand(),
        SummaryCommand(),
        ClipboardCommand(),
        ImageCommand(),
        HooksCommand(),
        InstallCommand(),
        SandboxCommand(),
        MaxTokensCommand(),
        PluginsCommand(),
        SkillsCommand(),
        SkillCommand(),
        RulesCommand(),
        ImportCommand(),
        BookmarkCommand(),
        TaskCommand(),
        SearchCommand(),
        FetchCommand(),
        ScanCommand(),
        RunCodeCommand(),
        PickCommand(),
        WatchCommand(),
        AskCommand(),
        MemoryReloadCommand(),
        McpCommand(),
        ContextCommand(),
    ]
    registry: dict[str, Command] = {}
    for command in commands:
        registry[command.name] = command
        for alias in command.aliases:
            registry[alias] = command
    return registry


def build_custom_command_registry(commands_map: dict[str, str]) -> dict[str, Command]:
    """Build a registry of CustomCommand objects from project memory commands."""
    registry: dict[str, Command] = {}
    for name, description in commands_map.items():
        registry[name] = CustomCommand(name, description)
    return registry
