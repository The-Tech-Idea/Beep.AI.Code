"""Tests for rules loading and resolver behavior."""

from __future__ import annotations

from pathlib import Path

from beep.rules.loader import load_rules
from beep.rules.resolver import build_rules_context, resolve_rules_for_path


def test_load_rules_in_order(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    (home / ".beepai").mkdir(parents=True)
    (home / ".beepai" / "rules.md").write_text("home rule", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("agents rule", encoding="utf-8")
    (tmp_path / ".beep").mkdir()
    (tmp_path / ".beep" / "rules.md").write_text("workspace rule", encoding="utf-8")
    (tmp_path / ".beep" / "rules").mkdir()
    (tmp_path / ".beep" / "rules" / "10-python.md").write_text(
        "---\napplies_to: \"**/*.py\"\n---\npython rule",
        encoding="utf-8",
    )

    rules, errors = load_rules(tmp_path)
    assert not errors
    assert [r.source.name for r in rules] == ["rules.md", "AGENTS.md", "rules.md", "10-python.md"]


def test_resolve_rules_for_path_matches_glob(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".beep" / "rules"
    rules_dir.mkdir(parents=True)
    path = rules_dir / "10-python.md"
    path.write_text("---\napplies_to: \"**/*.py\"\n---\npython-only", encoding="utf-8")
    rules, _ = load_rules(tmp_path)
    selected_py = resolve_rules_for_path(rules, "src/app.py")
    selected_md = resolve_rules_for_path(rules, "README.md")
    assert len(selected_py) == 1
    assert len(selected_md) == 0


def test_build_rules_context_renders_sources(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("do x", encoding="utf-8")
    rules, _ = load_rules(tmp_path)
    context = build_rules_context(rules)
    assert "Active Rules" in context
    assert "AGENTS.md" in context
    assert "do x" in context
