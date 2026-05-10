"""Resolve applicable rules and render prompt context."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from beep.rules.loader import LoadedRule


def resolve_rules_for_paths(
    rules: list[LoadedRule],
    target_paths: list[str],
) -> list[LoadedRule]:
    """Return rules applicable to any of the given paths (union), preserving order."""
    if not target_paths:
        return list(rules)
    seen: set[int] = set()
    selected: list[LoadedRule] = []
    for path in target_paths:
        for rule in resolve_rules_for_path(rules, target_path=path):
            rule_id = id(rule)
            if rule_id not in seen:
                seen.add(rule_id)
                selected.append(rule)
    return selected


def resolve_rules_for_path(
    rules: list[LoadedRule],
    target_path: str | None = None,
) -> list[LoadedRule]:
    """Return rules applicable to a path, preserving load order."""
    if not target_path:
        return list(rules)
    normalized = str(Path(target_path)).replace("\\", "/")
    selected: list[LoadedRule] = []
    for rule in rules:
        if not rule.applies_to:
            selected.append(rule)
            continue
        if fnmatch(normalized, rule.applies_to):
            selected.append(rule)
    return selected


def build_rules_context(rules: list[LoadedRule], target_path: str | None = None) -> str:
    """Build prompt section from resolved rules."""
    resolved = resolve_rules_for_path(rules, target_path=target_path)
    if not resolved:
        return ""
    parts = ["## Active Rules"]
    for rule in resolved:
        parts.append(f"\n### {rule.source.name}\n{rule.content}")
    return "\n".join(parts).strip()
