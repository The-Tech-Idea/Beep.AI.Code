"""Load skills from markdown files with YAML-like frontmatter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from beep.skills.models import SkillDefinition


def _discover_skill_roots(workspace_root: Path) -> list[Path]:
    roots = [
        Path.home() / ".beepai" / "skills",
        workspace_root / ".beep" / "skills",
    ]
    env_dir = os.environ.get("BEEP_SKILLS_DIR")
    if env_dir:
        roots.append(Path(env_dir))
    return roots


def _parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    if not content.startswith("---\n"):
        return {}, content.strip()

    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content.strip()

    header = content[4:end].strip()
    body = content[end + 5 :].strip()
    data: dict[str, object] = {}

    for raw_line in header.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            parts = [part.strip().strip("\"'") for part in value[1:-1].split(",") if part.strip()]
            data[key] = parts
            continue
        if value.lower() in {"true", "false"}:
            data[key] = value.lower() == "true"
            continue
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            data[key] = int(value)
            continue
        data[key] = value.strip("\"'")
    return data, body


def load_skills(workspace_root: Path) -> tuple[list[SkillDefinition], list[str], list[Path]]:
    """Load all skills from discovery roots."""
    skills: list[SkillDefinition] = []
    errors: list[str] = []
    roots = _discover_skill_roots(workspace_root)

    for root in roots:
        if not root.exists():
            continue
        for skill_path in root.rglob("*.md"):
            try:
                raw = skill_path.read_text(encoding="utf-8")
                frontmatter, body = _parse_frontmatter(raw)
                name = str(frontmatter.get("name") or skill_path.stem)
                description = str(frontmatter.get("description") or "")
                inject = str(frontmatter.get("inject") or "user_once")
                priority = int(str(frontmatter.get("priority") or 0))
                triggers_raw = frontmatter.get("triggers") or []
                if isinstance(triggers_raw, list):
                    triggers = [str(t).strip() for t in triggers_raw if str(t).strip()]
                else:
                    triggers = [str(triggers_raw).strip()] if str(triggers_raw).strip() else []
                skills.append(
                    SkillDefinition(
                        name=name,
                        description=description,
                        triggers=triggers,
                        inject=inject,
                        priority=priority,
                        body=body,
                        source=str(skill_path),
                    )
                )
            except Exception as exc:
                errors.append(f"{skill_path}: {exc}")

    return skills, errors, roots


def server_skills_to_definitions(server_skills: list[dict[str, Any]]) -> list[SkillDefinition]:
    """Convert server skill dicts to SkillDefinition objects.

    Server skills use ``inject_mode`` in the DB but the CLI's SkillDefinition
    uses ``inject``.  This adapter normalizes the format.
    """
    definitions = []
    for s in server_skills:
        definitions.append(
            SkillDefinition(
                name=str(s.get("name", "")),
                description=str(s.get("description") or ""),
                triggers=[str(t).strip() for t in (s.get("triggers") or []) if str(t).strip()],
                inject=str(s.get("inject") or s.get("inject_mode") or "user_once"),
                priority=int(s.get("priority") or 0),
                body=str(s.get("body") or ""),
                source=str(s.get("source") or "server:global"),
            )
        )
    return definitions
