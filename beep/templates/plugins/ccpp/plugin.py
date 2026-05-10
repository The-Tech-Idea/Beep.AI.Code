"""C/C++ project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.ccpp import get_ccpp_cmake_library_template


class CCppTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "ccpp-templates"

    @property
    def description(self) -> str:
        return "Project templates for C/C++ applications."

    def get_templates(self) -> list[ProjectTemplate]:
        return [get_ccpp_cmake_library_template()]
