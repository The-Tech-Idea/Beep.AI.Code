"""Project template validation service."""

from __future__ import annotations

from pathlib import Path

from beep.templates.models import ProjectTemplate
from beep.templates.registry import ProjectTemplateRegistry


class ValidationResult:
    def __init__(self, template: ProjectTemplate, project_root: Path) -> None:
        self.template = template
        self.project_root = project_root
        self.missing: list[str] = []
        self.present: list[str] = []
        self.extras: list[str] = []
        self.is_valid = True

    @property
    def score(self) -> float:
        total = len(self.template.required_file_paths())
        if total == 0:
            return 1.0
        return len(self.present) / total

    def to_dict(self) -> dict:
        return {
            "template": self.template.full_name,
            "valid": self.is_valid,
            "score": round(self.score, 2),
            "missing_files": self.missing,
            "present_files": self.present,
            "extra_files": self.extras,
            "build_command": self.template.build_command,
            "test_command": self.template.test_command,
            "lint_command": self.template.lint_command,
        }


class ProjectTemplateValidator:
    """Validates projects against registered templates."""

    def __init__(self, registry: ProjectTemplateRegistry) -> None:
        self.registry = registry

    def validate(self, project_root: str) -> list[ValidationResult]:
        root = Path(project_root)
        matching = self.registry.match_project(project_root)
        results: list[ValidationResult] = []

        for template in matching:
            result = ValidationResult(template, root)
            for file_def in template.files:
                resolved = file_def.path.replace("{{name}}", root.name)
                if (root / resolved).exists():
                    result.present.append(file_def.path)
                elif file_def.required:
                    result.missing.append(file_def.path)
                    result.is_valid = False

            actual_files = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
            expected = {f.path.replace("{{name}}", root.name) for f in template.files}
            result.extras = sorted(actual_files - expected)
            results.append(result)

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def get_best_template(self, project_root: str) -> ValidationResult | None:
        results = self.validate(project_root)
        return results[0] if results else None
