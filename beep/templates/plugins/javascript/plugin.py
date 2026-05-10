"""JavaScript project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.javascript import (
    get_js_library_template,
    get_js_nodeapp_template,
)


class JavaScriptTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "javascript-templates"

    @property
    def description(self) -> str:
        return "Project templates for JavaScript applications and libraries."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_js_library_template(),
            get_js_nodeapp_template(),
        ]
