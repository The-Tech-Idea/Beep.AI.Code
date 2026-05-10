"""Project memory files (.beep.md, .beep/).

Similar to CLAUDE.md, these files provide project-specific instructions
to the AI assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectMemory:
    """Container for project-specific instructions."""

    global_instructions: str = ""
    commands: dict[str, str] = field(default_factory=dict)
    habits: list[str] = field(default_factory=list)
    ignored_patterns: list[str] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        """Return a Markdown section string of all loaded memory sub-sections."""
        return self.to_system_prompt()

    def to_system_prompt(self) -> str:
        """Convert to system prompt section."""
        parts = []

        if self.global_instructions:
            parts.append("## Project Instructions\n\n" + self.global_instructions)

        if self.habits:
            parts.append("## Project Habits\n\n" + "\n".join(f"- {h}" for h in self.habits))

        if self.commands:
            parts.append("## Project Commands\n\n" + "\n".join(
                f"- `{name}`: {desc}" for name, desc in self.commands.items()
            ))

        return "\n\n".join(parts)


def load_project_memory(workspace_root: Path) -> ProjectMemory:
    """Load project memory from workspace root.

    Searches for:
    - .beep.md (global instructions)
    - .beep/commands.md (custom commands)
    - .beep/habits.md (project habits)
    """
    memory = ProjectMemory()

    beep_md = workspace_root / ".beep.md"
    if beep_md.exists():
        memory.global_instructions = beep_md.read_text(encoding="utf-8").strip()

    beep_dir = workspace_root / ".beep"
    if beep_dir.is_dir():
        commands_file = beep_dir / "commands.md"
        if commands_file.exists():
            memory.commands = _parse_commands(commands_file.read_text(encoding="utf-8"))

        habits_file = beep_dir / "habits.md"
        if habits_file.exists():
            memory.habits = _parse_habits(habits_file.read_text(encoding="utf-8"))

        ignore_file = beep_dir / "ignore"
        if ignore_file.exists():
            memory.ignored_patterns = [
                line.strip()
                for line in ignore_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]

    return memory


def _parse_commands(content: str) -> dict[str, str]:
    """Parse commands.md format: `- command: description`."""
    commands = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            parts = line[2:].split(":", 1)
            if len(parts) == 2:
                commands[parts[0].strip()] = parts[1].strip()
    return commands


def _parse_habits(content: str) -> list[str]:
    """Parse habits.md format: `- habit`."""
    return [
        line.strip()[2:].strip()
        for line in content.splitlines()
        if line.strip().startswith("- ")
    ]
