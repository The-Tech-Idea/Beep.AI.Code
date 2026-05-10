"""Tests for skills loading and resolution."""

from __future__ import annotations

from pathlib import Path

from beep.skills.loader import load_skills
from beep.skills.resolver import SkillResolver


def test_load_skills_from_workspace(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".beep" / "skills"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("python.md").write_text(
        """---
name: python-helper
description: Python coding helper
triggers: [python, pytest]
inject: user_once
priority: 5
---
Prefer type hints and small focused tests.
""",
        encoding="utf-8",
    )

    skills, errors, _roots = load_skills(tmp_path)
    assert not errors
    assert len(skills) == 1
    assert skills[0].name == "python-helper"
    assert "python" in skills[0].triggers


def test_skill_resolver_matches_and_budget() -> None:
    from beep.skills.models import SkillDefinition

    skills = [
        SkillDefinition(
            name="python-helper",
            description="",
            triggers=["python"],
            inject="user_once",
            priority=1,
            body="Use type hints.",
            source="x.md",
        ),
        SkillDefinition(
            name="large-skill",
            description="",
            triggers=["python"],
            inject="user_once",
            priority=2,
            body="x" * 4000,
            source="y.md",
        ),
    ]
    resolver = SkillResolver(skills)
    matches = resolver.resolve("help with python tests", max_skills=3, budget_chars=3000)
    assert len(matches) == 1
    assert matches[0].skill.name == "python-helper"
