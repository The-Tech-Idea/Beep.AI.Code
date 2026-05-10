"""Code snippet template tool for agent framework.

Uses the existing code snippet template system (catalog.py, discovery.py, rendering.py)
to generate individual code files from templates like fastapi-route, react-component, etc.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beep.agent.tools.base import BaseTool, ToolResult
from beep.templates.discovery import collect_templates, get_template_by_name
from beep.templates.rendering import generate_from_template, resolve_template_variables


class CodeSnippetTool(BaseTool):
    """Generate a code snippet from a built-in template."""

    @property
    def name(self) -> str:
        return "code_snippet"

    @property
    def description(self) -> str:
        return "Generate a code file from a snippet template (e.g., fastapi-route, react-component, python-class)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "template_name": {
                "type": "string",
                "description": "Name of the snippet template (e.g., 'fastapi-route', 'react-component').",
            },
            "output_path": {
                "type": "string",
                "description": "Path where the generated file should be written.",
            },
            "variables": {
                "type": "object",
                "description": "Template variables as key-value pairs.",
                "additionalProperties": {"type": "string"},
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["variables"]

    @property
    def category(self) -> str:
        return "project"

    @property
    def read_only_safe(self) -> bool:
        return False

    async def execute(self, **kwargs: Any) -> ToolResult:
        template_name = kwargs.get("template_name", "")
        output_path = kwargs.get("output_path", "")
        variables = kwargs.get("variables", {})

        if not template_name:
            available = [t.name for t in collect_templates()]
            return ToolResult(
                success=False,
                output="",
                error=f"template_name is required. Available: {', '.join(available)}",
                is_error=True,
            )
        if not output_path:
            return ToolResult(
                success=False, output="", error="output_path is required", is_error=True
            )

        template = get_template_by_name(template_name)
        if not template:
            available = [t.name for t in collect_templates()]
            return ToolResult(
                success=False,
                output="",
                error=f"Template '{template_name}' not found. Available: {', '.join(available)}",
                is_error=True,
            )

        resolved = variables or {}
        missing_vars = [v for v in template.variables if v not in resolved]
        if missing_vars:
            return ToolResult(
                success=False,
                output="",
                error=f"Missing variables: {', '.join(missing_vars)}. Provide them in the variables parameter.",
                is_error=True,
            )

        target = Path(output_path)
        if target.suffix and not template.file_extension:
            pass
        elif template.file_extension and not target.suffix:
            target = target.with_suffix(template.file_extension)

        if target.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File '{target}' already exists.",
                is_error=True,
            )

        generate_from_template(template, target, resolved)

        lines = [
            f"Generated '{template.name}' snippet at '{target}'.",
            f"Template: {template.description}",
            f"Variables used: {', '.join(f'{k}={v}' for k, v in resolved.items())}"
            if resolved
            else "No variables",
        ]
        return ToolResult(success=True, output="\n".join(lines))


class CodeSnippetListTool(BaseTool):
    """List available code snippet templates."""

    @property
    def name(self) -> str:
        return "code_snippet_list"

    @property
    def description(self) -> str:
        return "List available code snippet templates and their variables."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "category": {
                "type": "string",
                "description": "Optional category filter (e.g., 'python', 'typescript').",
            },
        }

    @property
    def optional_params(self) -> list[str]:
        return ["category"]

    @property
    def category(self) -> str:
        return "project"

    @property
    def read_only_safe(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> ToolResult:
        category = kwargs.get("category", "")
        templates = collect_templates()
        if category:
            templates = [t for t in templates if t.category == category]

        if not templates:
            return ToolResult(success=True, output="No templates found.")

        lines = ["Available code snippet templates:"]
        for t in templates:
            vars_str = ", ".join(f"{{{v}}}" for v in t.variables) if t.variables else "none"
            lines.append(f"  - {t.name} ({t.category}): {t.description}")
            lines.append(f"    Variables: {vars_str}")
            lines.append(f"    Extension: {t.file_extension or 'auto'}")
        return ToolResult(success=True, output="\n".join(lines))


def build_snippet_tools() -> tuple[BaseTool, ...]:
    return (CodeSnippetTool(), CodeSnippetListTool())
