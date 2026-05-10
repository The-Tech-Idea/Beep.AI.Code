"""Public template facade.

Keeps the stable template API while template-domain responsibilities live in
dedicated catalog, discovery, and rendering modules.
"""

from __future__ import annotations

from beep.templates.catalog import BUILTIN_TEMPLATES, Template
from beep.templates.discovery import get_template_by_name, list_templates
from beep.templates.rendering import display_templates, generate_from_template

__all__ = [
    "BUILTIN_TEMPLATES",
    "Template",
    "display_templates",
    "generate_from_template",
    "get_template_by_name",
    "list_templates",
]
