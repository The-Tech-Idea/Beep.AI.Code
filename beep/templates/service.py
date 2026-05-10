"""Template-domain orchestration for command surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from beep.templates.catalog import Template


def parse_template_variables(entries: list[str] | None) -> dict[str, str]:
    """Parse key=value template variable arguments."""
    variables: dict[str, str] = {}
    if not entries:
        return variables
    for entry in entries:
        if "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        variables[key] = value
    return variables


def show_template_listing(
    *,
    workspace_root: Path | str | None,
    category: str | None,
    list_templates: Callable[..., list[Template]],
    display_templates: Callable[[list[Template]], None],
) -> None:
    """Load and display templates for a command surface."""
    templates = list_templates(category, workspace_root=workspace_root)
    display_templates(templates)


def generate_template_file(
    *,
    name: str,
    output_path: Path,
    raw_variables: list[str] | None,
    workspace_root: Path | str | None,
    get_template_by_name: Callable[..., Template | None],
    list_templates: Callable[..., list[Template]],
    generate_from_template: Callable[[Template, Path, dict[str, str]], Path],
) -> Path:
    """Resolve a named template and render it to disk."""
    template = get_template_by_name(name, workspace_root=workspace_root)
    if template is None:
        available = ", ".join(
            template_item.name
            for template_item in list_templates(workspace_root=workspace_root)
        )
        raise ValueError(f"Unknown template: {name}. Available: {available}")
    variables = parse_template_variables(raw_variables)
    return generate_from_template(template, output_path, variables)