"""Go project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.go import (
    get_go_cli_template,
    get_go_webapi_template,
)


class GoTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "go-templates"

    @property
    def description(self) -> str:
        return "Project templates for Go applications."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_go_cli_template(),
            get_go_webapi_template(),
        ]
