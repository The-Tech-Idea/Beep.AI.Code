"""Tests for template discovery and generation."""

from __future__ import annotations

from pathlib import Path

from beep.templates.generator import generate_from_template, get_template_by_name, list_templates


def test_list_templates_includes_workspace_custom(tmp_path: Path) -> None:
    template_dir = tmp_path / ".beep" / "templates"
    template_dir.mkdir(parents=True)
    template_dir.joinpath("service.md").write_text(
        """---
name: service-class
category: python
description: Service class template
extension: .py
variables: class_name
---
class {class_name}:
    pass
""",
        encoding="utf-8",
    )

    templates = list_templates(workspace_root=tmp_path)
    names = {template.name for template in templates}
    assert "service-class" in names


def test_custom_template_overrides_builtin(tmp_path: Path) -> None:
    template_dir = tmp_path / ".beep" / "templates"
    template_dir.mkdir(parents=True)
    template_dir.joinpath("override.md").write_text(
        """---
name: python-class
category: python
description: overridden
extension: .py
variables: class_name
---
class {class_name}:
    def __repr__(self): return "{class_name}"
""",
        encoding="utf-8",
    )

    template = get_template_by_name("python-class", workspace_root=tmp_path)
    assert template is not None
    assert "overridden" in template.description
    assert template.source.endswith("override.md")


def test_generate_from_custom_template(tmp_path: Path) -> None:
    template_dir = tmp_path / ".beep" / "templates"
    template_dir.mkdir(parents=True)
    template_dir.joinpath("simple.md").write_text(
        """---
name: simple
category: misc
description: simple
extension: .txt
variables: name
---
Hello {name}
""",
        encoding="utf-8",
    )

    template = get_template_by_name("simple", workspace_root=tmp_path)
    assert template is not None
    output = generate_from_template(template, tmp_path / "out", {"name": "Beep"})
    assert output.suffix == ".txt"
    assert output.read_text(encoding="utf-8") == "Hello Beep"
