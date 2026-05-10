"""Project template registry and discovery."""

from __future__ import annotations

from pathlib import Path

from beep.templates.models import ProjectTemplate
from beep.templates.plugin import ProjectTemplatePlugin


class ProjectTemplateRegistry:
    """Registry for project template plugins.

    Collects templates from all registered plugins and provides
    lookup by language, framework, or project detection.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, ProjectTemplatePlugin] = {}

    def register(self, plugin: ProjectTemplatePlugin) -> None:
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)

    def get_templates(self, language: str = "", framework: str = "") -> list[ProjectTemplate]:
        templates: list[ProjectTemplate] = []
        for plugin in self._plugins.values():
            for template in plugin.get_templates():
                if language and template.language != language:
                    continue
                if framework and template.framework != framework:
                    continue
                templates.append(template)
        return templates

    def get_template(self, full_name: str) -> ProjectTemplate | None:
        for plugin in self._plugins.values():
            for template in plugin.get_templates():
                if template.full_name == full_name or template.name == full_name:
                    return template
        return None

    def match_project(self, project_root: str) -> list[ProjectTemplate]:
        matches: list[ProjectTemplate] = []
        for plugin in self._plugins.values():
            matches.extend(plugin.matches_project(project_root))
        return matches

    def validate_project(self, project_root: str, template_name: str) -> dict | None:
        for plugin in self._plugins.values():
            result = plugin.validate_project(project_root, template_name)
            if "error" not in result:
                return result
        return None

    def list_languages(self) -> list[str]:
        languages: set[str] = set()
        for plugin in self._plugins.values():
            for template in plugin.get_templates():
                languages.add(template.language)
        return sorted(languages)

    def list_frameworks(self, language: str) -> list[str]:
        frameworks: set[str] = set()
        for plugin in self._plugins.values():
            for template in plugin.get_templates():
                if template.language == language and template.framework:
                    frameworks.add(template.framework)
        return sorted(frameworks)
