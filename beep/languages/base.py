"""Base interface for language-specific project intelligence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProjectCommand:
    """A runnable project command with optional working directory."""

    name: str
    command: list[str]
    description: str
    cwd: str | None = None

    @property
    def shell_form(self) -> str:
        return " ".join(self.command)


@dataclass
class ProjectProfile:
    """Aggregated project configuration for agent prompt injection."""

    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    build_commands: list[ProjectCommand] = field(default_factory=list)
    test_commands: list[ProjectCommand] = field(default_factory=list)
    lint_commands: list[ProjectCommand] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        lines: list[str] = []
        if self.languages:
            lines.append(f"Detected languages: {', '.join(self.languages)}")
        if self.frameworks:
            lines.append(f"Detected frameworks: {', '.join(self.frameworks)}")
        if self.build_commands:
            lines.append("Build commands:")
            for cmd in self.build_commands:
                cwd = f" (cwd: {cmd.cwd})" if cmd.cwd else ""
                lines.append(f"  - {cmd.name}: {cmd.shell_form}{cwd}")
        if self.test_commands:
            lines.append("Test commands:")
            for cmd in self.test_commands:
                cwd = f" (cwd: {cmd.cwd})" if cmd.cwd else ""
                lines.append(f"  - {cmd.name}: {cmd.shell_form}{cwd}")
        if self.lint_commands:
            lines.append("Lint commands:")
            for cmd in self.lint_commands:
                cwd = f" (cwd: {cmd.cwd})" if cmd.cwd else ""
                lines.append(f"  - {cmd.name}: {cmd.shell_form}{cwd}")
        if not lines:
            return ""
        return "\n".join(lines)


class LanguageAdapter(ABC):
    """Base adapter for language-specific project intelligence."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def extensions(self) -> list[str]:
        pass

    @abstractmethod
    def detect(self, root_path: str) -> bool:
        pass

    @abstractmethod
    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        pass

    @abstractmethod
    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        pass

    @abstractmethod
    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        pass

    @abstractmethod
    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        pass

    def get_frameworks(self, root_path: str) -> list[str]:
        return []

    def get_package_managers(self, root_path: str) -> list[str]:
        return []

    def get_commands_for_file(self, source_file: str, root_path: str) -> list[ProjectCommand]:
        commands: list[ProjectCommand] = []
        commands.extend(self.get_build_commands(root_path))
        commands.extend(self.get_test_commands(root_path))
        commands.extend(self.get_lint_commands(root_path))
        return commands
