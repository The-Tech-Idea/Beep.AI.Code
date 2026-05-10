"""Base class for project template plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from beep.templates.models import ProjectTemplate


class ProjectTemplatePlugin(ABC):
    """Base class for project template plugins.

    Each plugin provides templates for one or more language/framework combos.
    Plugins are discovered by the registry and used for scaffolding and validation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable plugin description."""

    @abstractmethod
    def get_templates(self) -> list[ProjectTemplate]:
        """Return all templates this plugin provides."""

    def matches_project(self, project_root: str) -> list[ProjectTemplate]:
        """Find templates that match an existing project."""
        root = Path(project_root)
        matches: list[ProjectTemplate] = []
        for template in self.get_templates():
            missing = 0
            required = template.required_file_paths()
            if not required:
                continue
            for file_path in required:
                resolved = file_path.replace("{{name}}", root.name)
                if not (root / resolved).exists():
                    missing += 1
            if missing <= len(required) * 0.5:
                matches.append(template)
        return matches

    def validate_project(self, project_root: str, template_name: str) -> dict[str, Any]:
        """Validate a project against a specific template."""
        root = Path(project_root)
        templates = {t.name: t for t in self.get_templates()}
        template = templates.get(template_name)
        if not template:
            return {"valid": False, "error": f"Template '{template_name}' not found."}

        results: dict[str, Any] = {
            "template": template_name,
            "valid": True,
            "missing_files": [],
            "present_files": [],
            "recommendations": [],
        }

        for file_def in template.files:
            resolved = file_def.path.replace("{{name}}", root.name)
            if (root / resolved).exists():
                results["present_files"].append(file_def.path)
            elif file_def.required:
                results["missing_files"].append(file_def.path)
                results["valid"] = False

        if template.build_command:
            results["recommendations"].append(f"Build command available: {template.build_command}")
        if template.test_command:
            results["recommendations"].append(f"Test command available: {template.test_command}")
        if template.lint_command:
            results["recommendations"].append(f"Lint command available: {template.lint_command}")

        return results
