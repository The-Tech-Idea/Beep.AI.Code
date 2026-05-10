"""Template discovery and loading for built-in and external template packs."""

from __future__ import annotations

import os
from pathlib import Path

from beep.templates.catalog import BUILTIN_TEMPLATES, Template


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        return {}, content.strip()
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content.strip()
    header = content[4:end]
    body = content[end + 5 :].strip()
    meta: dict[str, str] = {}
    for raw in header.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("\"'")
    return meta, body


def discover_template_roots(workspace_root: Path | None = None) -> list[Path]:
    roots = [Path.home() / ".beepai" / "templates"]
    if workspace_root:
        roots.append(workspace_root / ".beep" / "templates")
    env_dir = os.environ.get("BEEP_TEMPLATES_DIR")
    if env_dir:
        roots.append(Path(env_dir))
    return roots


def load_external_templates(workspace_root: Path | None = None) -> list[Template]:
    templates: list[Template] = []
    for root in discover_template_roots(workspace_root):
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            try:
                raw = path.read_text(encoding="utf-8")
                meta, body = parse_frontmatter(raw)
                name = meta.get("name", path.stem)
                category = meta.get("category", "custom")
                description = meta.get("description", f"Custom template from {path.name}")
                extension = meta.get("extension", "")
                variables_raw = meta.get("variables", "")
                variables = [item.strip() for item in variables_raw.split(",") if item.strip()]
                templates.append(
                    Template(
                        name=name,
                        description=description,
                        category=category,
                        content=body,
                        variables=variables,
                        file_extension=extension,
                        source=str(path),
                    )
                )
            except Exception:
                continue
    return templates


def collect_templates(workspace_root: Path | None = None) -> list[Template]:
    """Collect built-in and external templates with later sources overriding by name."""
    merged: dict[str, Template] = {template.name: template for template in BUILTIN_TEMPLATES}
    for template in load_external_templates(workspace_root):
        merged[template.name] = template
    return sorted(merged.values(), key=lambda template: template.name)


def list_templates(
    category: str | None = None,
    *,
    workspace_root: Path | None = None,
) -> list[Template]:
    templates = collect_templates(workspace_root)
    if category:
        return [template for template in templates if template.category == category]
    return templates


def get_template_by_name(name: str, workspace_root: Path | None = None) -> Template | None:
    for template in collect_templates(workspace_root):
        if template.name == name:
            return template
    return None