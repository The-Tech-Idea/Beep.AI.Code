"""Python project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.python import (
    get_python_library_template,
    get_python_cli_template,
    get_python_webapp_template,
)


class PythonTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "python-templates"

    @property
    def description(self) -> str:
        return "Project templates for Python applications and libraries."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_python_library_template(),
            get_python_cli_template(),
            get_python_webapp_template(),
        ]
