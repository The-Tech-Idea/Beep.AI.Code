"""Rust project template plugin."""

from __future__ import annotations

from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.models import ProjectTemplate
from beep.templates.plugins.rust import (
    get_rust_library_template,
    get_rust_cli_template,
)


class RustTemplatePlugin(ProjectTemplatePlugin):
    @property
    def name(self) -> str:
        return "rust-templates"

    @property
    def description(self) -> str:
        return "Project templates for Rust applications and libraries."

    def get_templates(self) -> list[ProjectTemplate]:
        return [
            get_rust_library_template(),
            get_rust_cli_template(),
        ]
