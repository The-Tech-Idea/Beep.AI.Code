"""Tests for skill materialization."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.integrations.models import CatalogEntry, EntryKind, TrustTier
from beep.integrations.skills_source import (
    _skills_target_root,
    _skill_target_dir,
    materialize_skill,
)


def _make_skill_entry(**kwargs: object) -> CatalogEntry:
    defaults: dict[str, object] = {
        "id": "test-skill",
        "kind": EntryKind.skill,
        "name": "Test Skill",
        "summary": "A test skill",
        "trust": TrustTier.first_party,
        "tags": ["test"],
        "source_url": "",
        "version": "",
    }
    defaults.update(kwargs)
    return CatalogEntry(**defaults)  # type: ignore[arg-type]


class TestSkillMaterialize:
    def test_materialize_creates_skill_md(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(Path, "home", lambda: Path(tmp))

            entry = _make_skill_entry(
                id="code-review",
                name="Code Review",
                summary="Review code",
            )
            target = materialize_skill(entry)
            assert target.exists()
            assert target.name == "code-review"

            skill_file = target / "skill.md"
            assert skill_file.exists()
            content = skill_file.read_text()
            assert "Code Review" in content
            assert "Review code" in content

    def test_materialize_with_source_url_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(Path, "home", lambda: Path(tmp))

            entry = _make_skill_entry(
                id="open-design",
                name="Open Design",
                source_url="https://example.com/nonexistent-repo",
                version="nonexistent",
                trust=TrustTier.external,
            )
            target = materialize_skill(entry)
            assert target.exists()
            skill_file = target / "skill.md"
            assert skill_file.exists()
            content = skill_file.read_text()
            assert "Installed via Beep integration catalog" in content

    def test_skill_target_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(Path, "home", lambda: Path(tmp))
            target = _skill_target_dir("my-skill")
            assert target == Path(tmp) / ".beepai" / "skills" / "my-skill"

    def test_skills_target_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(Path, "home", lambda: Path(tmp))
            root = _skills_target_root()
            assert root == Path(tmp) / ".beepai" / "skills"
