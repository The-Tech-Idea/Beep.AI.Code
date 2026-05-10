"""C# project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.csharp import (
    get_csharp_library_template,
    get_csharp_webapi_template,
)


class CSharpTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "csharp-templates"

    @property
    def description(self) -> str:
        return "Project templates for C# and .NET applications."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_csharp_library_template(),
            get_csharp_webapi_template(),
        ]
