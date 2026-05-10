"""Project template plugin system."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile, TemplateRequirement
from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.registry import ProjectTemplateRegistry
from beep.templates.validator import ProjectTemplateValidator, ValidationResult

__all__ = [
    "ProjectTemplate",
    "ProjectTemplatePlugin",
    "ProjectTemplateRegistry",
    "ProjectTemplateValidator",
    "TemplateFile",
    "TemplateRequirement",
    "ValidationResult",
]
