"""Template variable resolution, file generation, and display helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from rich.prompt import Prompt
from rich.table import Table

from beep.templates.catalog import Template



from beep.utils.console import get_console
def resolve_template_variables(
    template: Template,
    variables: dict[str, str] | None = None,
    *,
    ask: Callable[..., str] = Prompt.ask,
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for variable in template.variables:
        if variables and variable in variables:
            resolved[variable] = variables[variable]
        else:
            resolved[variable] = ask(f"  {variable}")
    return resolved


def generate_from_template(
    template: Template,
    output_path: Path,
    variables: dict[str, str] | None = None,
) -> Path:
    """Generate a file from a template."""
    resolved_variables = resolve_template_variables(template, variables)
    content = template.content.format(**resolved_variables)

    if template.file_extension and not output_path.suffix:
        output_path = output_path.with_suffix(template.file_extension)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def display_templates(templates: list[Template]) -> None:
    """Display available templates."""
    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Description")
    table.add_column("Variables")
    table.add_column("Source")

    for template in templates:
        variables = ", ".join(f"{{{value}}}" for value in template.variables) if template.variables else "none"
        source = template.source if template.source == "builtin" else Path(template.source).name
        table.add_row(template.name, template.category, template.description, variables, source)

    get_console().print(table)