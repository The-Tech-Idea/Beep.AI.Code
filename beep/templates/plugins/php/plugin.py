"""PHP project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.php import (
    get_php_library_template,
    get_php_laravel_template,
)


class PHPPluginTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "php-templates"

    @property
    def description(self) -> str:
        return "Project templates for PHP applications and libraries."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_php_library_template(),
            get_php_laravel_template(),
        ]
