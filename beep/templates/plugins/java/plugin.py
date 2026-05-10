"""Java project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.java import (
    get_java_maven_library_template,
    get_java_springboot_template,
)


class JavaTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "java-templates"

    @property
    def description(self) -> str:
        return "Project templates for Java applications and libraries."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_java_maven_library_template(),
            get_java_springboot_template(),
        ]
