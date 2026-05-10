"""Project scaffolding tool for agent framework."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.templates.registry import ProjectTemplateRegistry


class ProjectScaffoldTool(BaseTool):
    """Scaffold a new project from a template."""

    def __init__(self, registry: ProjectTemplateRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "project_scaffold"

    @property
    def description(self) -> str:
        return "Create a new project from a language-specific template."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "project_name": {
                "type": "string",
                "description": "Name of the new project.",
            },
            "template": {
                "type": "string",
                "description": "Template full name (e.g., 'python/fastapi', 'csharp/aspnetcore').",
            },
            "directory": {
                "type": "string",
                "description": "Directory to create the project in (default: project_name).",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["directory"]

    @property
    def category(self) -> str:
        return "project"

    @property
    def read_only_safe(self) -> bool:
        return False

    async def execute(self, **kwargs: Any) -> ToolResult:
        project_name = kwargs.get("project_name", "")
        template_name = kwargs.get("template", "")
        directory = kwargs.get("directory", project_name)

        if not project_name:
            return ToolResult(
                success=False, output="", error="project_name is required", is_error=True
            )
        if not template_name:
            return ToolResult(success=False, output="", error="template is required", is_error=True)

        template = self._registry.get_template(template_name)
        if not template:
            available = [t.full_name for t in self._registry.get_templates()]
            return ToolResult(
                success=False,
                output="",
                error=f"Template '{template_name}' not found. Available: {', '.join(available)}",
                is_error=True,
            )

        target = Path(directory) if directory else Path(project_name)
        if target.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Directory '{target}' already exists.",
                is_error=True,
            )

        created: list[str] = []
        for file_def in template.files:
            file_path = file_def.resolve_path(str(target), project_name)
            file_content = file_def.resolve_content(project_name)
            p = Path(file_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(file_content, encoding="utf-8")
            created.append(str(p.relative_to(target)))

        lines = [
            f"Project '{project_name}' scaffolded from template '{template.full_name}'.",
            f"Directory: {target}",
            f"Created {len(created)} files:",
        ]
        for path in sorted(created):
            lines.append(f"  {path}")
        if template.build_command:
            lines.append(f"\nBuild: {template.build_command}")
        if template.test_command:
            lines.append(f"Test: {template.test_command}")

        return ToolResult(success=True, output="\n".join(lines))


class ProjectValidateTool(BaseTool):
    """Validate an existing project against templates."""

    def __init__(self, registry: ProjectTemplateRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "project_validate"

    @property
    def description(self) -> str:
        return "Validate an existing project against language-specific templates."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "project_path": {
                "type": "string",
                "description": "Path to the project directory.",
            },
            "template": {
                "type": "string",
                "description": "Optional template name to validate against.",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["template"]

    @property
    def category(self) -> str:
        return "project"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        project_path = kwargs.get("project_path", "")
        if not project_path:
            return ToolResult(
                success=False, output="", error="project_path is required", is_error=True
            )

        target = Path(project_path)
        if not target.is_dir():
            return ToolResult(
                success=False,
                output="",
                error=f"'{project_path}' is not a directory.",
                is_error=True,
            )

        template_name = kwargs.get("template", "")
        if template_name:
            result = self._registry.validate_project(project_path, template_name)
            if not result:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Template '{template_name}' not found.",
                    is_error=True,
                )
            lines = [
                f"Validation result for template '{template_name}':",
                f"  Valid: {result.get('valid', False)}",
            ]
            if result.get("missing_files"):
                lines.append(f"  Missing: {', '.join(result['missing_files'])}")
            if result.get("recommendations"):
                lines.append("  Recommendations:")
                for rec in result["recommendations"]:
                    lines.append(f"    - {rec}")
            return ToolResult(success=True, output="\n".join(lines))

        matches = self._registry.match_project(project_path)
        if not matches:
            return ToolResult(
                success=True,
                output=f"No matching templates found for project at '{project_path}'.",
            )

        lines = [f"Matching templates for '{project_path}':"]
        for t in matches:
            lines.append(f"  - {t.full_name}: {t.description}")
        return ToolResult(success=True, output="\n".join(lines))


def build_template_tools(
    *,
    registry: ProjectTemplateRegistry,
) -> tuple[BaseTool, ...]:
    return (
        ProjectScaffoldTool(registry),
        ProjectValidateTool(registry),
    )
