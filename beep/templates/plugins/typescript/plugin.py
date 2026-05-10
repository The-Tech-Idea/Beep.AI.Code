"""TypeScript project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.typescript import (
    get_ts_library_template,
    get_ts_nodeapp_template,
)


class TypeScriptTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "typescript-templates"

    @property
    def description(self) -> str:
        return "Project templates for TypeScript applications and libraries."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_ts_library_template(),
            get_ts_nodeapp_template(),
        ]
