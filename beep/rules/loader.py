"""Load user/workspace rules with deterministic precedence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class LoadedRule:
    source: Path
    content: str
    applies_to: str | None = None


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        return {}, content.strip()
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content.strip()
    header = content[4:end]
    body = content[end + 5 :].strip()
    data: dict[str, str] = {}
    for raw in header.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip().strip("\"'")
    return data, body


def _load_rule_file(path: Path) -> LoadedRule | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    frontmatter, body = _parse_frontmatter(text)
    return LoadedRule(source=path, content=body, applies_to=frontmatter.get("applies_to"))


def load_rules(workspace_root: Path) -> tuple[list[LoadedRule], list[str]]:
    """Load rules in ascending precedence order."""
    rules: list[LoadedRule] = []
    errors: list[str] = []

    ordered_files = [
        Path.home() / ".beepai" / "rules.md",
        workspace_root / "AGENTS.md",
        workspace_root / ".beep" / "rules.md",
    ]
    for file_path in ordered_files:
        try:
            loaded = _load_rule_file(file_path)
            if loaded:
                rules.append(loaded)
        except Exception as exc:
            errors.append(f"{file_path}: {exc}")

    rules_dir = workspace_root / ".beep" / "rules"
    if rules_dir.exists():
        for path in sorted(rules_dir.glob("*.md")):
            try:
                loaded = _load_rule_file(path)
                if loaded:
                    rules.append(loaded)
            except Exception as exc:
                errors.append(f"{path}: {exc}")

    return rules, errors
