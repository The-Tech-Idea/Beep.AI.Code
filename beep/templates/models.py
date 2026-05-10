"""Models for project template plugin system."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TemplateFile:
    """A file in a project template with optional templated content."""

    path: str
    content: str = ""
    description: str = ""
    required: bool = True
    is_executable: bool = False

    def resolve_path(self, project_root: str, project_name: str) -> str:
        resolved = self.path.replace("{{name}}", project_name)
        return str(Path(project_root) / resolved)

    def resolve_content(self, project_name: str, author: str = "") -> str:
        content = self.content.replace("{{name}}", project_name)
        content = content.replace("{{author}}", author)
        return content


@dataclass
class TemplateRequirement:
    """A requirement for a project template."""

    name: str
    version: str = "*"
    description: str = ""


@dataclass
class ProjectTemplate:
    """A project template that can scaffold or validate projects."""

    name: str
    language: str
    framework: str = ""
    description: str = ""
    files: list[TemplateFile] = field(default_factory=list)
    requirements: list[TemplateRequirement] = field(default_factory=list)
    build_command: str = ""
    test_command: str = ""
    lint_command: str = ""
    run_command: str = ""
    tags: list[str] = field(default_factory=list)
    min_version: str = ""
    recommended_tools: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        if self.framework:
            return f"{self.language}/{self.framework}"
        return self.language

    def required_file_paths(self) -> list[str]:
        return [f.path for f in self.files if f.required]

    def all_file_paths(self) -> list[str]:
        return [f.path for f in self.files]

    def to_prompt_section(self) -> str:
        lines = [
            f"Template: {self.full_name}",
            f"Description: {self.description}",
        ]
        if self.build_command:
            lines.append(f"Build: {self.build_command}")
        if self.test_command:
            lines.append(f"Test: {self.test_command}")
        if self.lint_command:
            lines.append(f"Lint: {self.lint_command}")
        if self.required_file_paths():
            lines.append(f"Required files: {', '.join(self.required_file_paths())}")
        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
        return "\n".join(lines)
