"""Skill materialization — fetch and install skill markdown packs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from beep.integrations.models import CatalogEntry


def _skills_target_root() -> Path:
    return Path.home() / ".beepai" / "skills"


def _skill_target_dir(entry_id: str) -> Path:
    return _skills_target_root() / entry_id


def materialize_skill(entry: CatalogEntry) -> Path:
    target = _skill_target_dir(entry.id)

    if entry.source_url and entry.version:
        try:
            _clone_from_git(entry.source_url, target, ref=entry.version)
            return target
        except Exception:
            pass

    target.mkdir(parents=True, exist_ok=True)
    body = (
        f"---\n"
        f"name: {entry.name}\n"
        f"description: {entry.summary}\n"
        f"triggers: [{', '.join(entry.tags)}]\n"
        f"inject: user_once\n"
        f"priority: 0\n"
        f"---\n\n"
        f"# {entry.name}\n\n"
        f"{entry.summary}\n\n"
        f"Source: {entry.source_url}\n\n"
        f"Installed via Beep integration catalog.\n"
    )
    target.joinpath("skill.md").write_text(body, encoding="utf-8")
    return target


def _clone_from_git(repo_url: str, target: Path, *, ref: str) -> None:
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(target)],
        check=True,
        capture_output=True,
        text=True,
    )
