"""Ruby project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.ruby import get_ruby_gem_template


class RubyTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "ruby-templates"

    @property
    def description(self) -> str:
        return "Project templates for Ruby gems and applications."

    def get_templates(self) -> list[ProjectTemplate]:
        return [get_ruby_gem_template()]
