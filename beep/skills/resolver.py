"""Resolve skills for a user prompt with simple relevance scoring."""

from __future__ import annotations

from beep.skills.models import SkillDefinition, SkillMatch


class SkillResolver:
    """Matches skills by trigger terms and applies budget limits."""

    def __init__(self, skills: list[SkillDefinition]) -> None:
        self._skills = skills

    def resolve(
        self,
        user_input: str,
        *,
        max_skills: int = 3,
        budget_chars: int = 3000,
    ) -> list[SkillMatch]:
        text = user_input.lower()
        matches: list[SkillMatch] = []

        for skill in self._skills:
            score = skill.priority
            for trigger in skill.triggers:
                normalized = trigger.lower().strip()
                if normalized and normalized in text:
                    score += 10
            if score > 0:
                matches.append(SkillMatch(skill=skill, score=score))

        matches.sort(key=lambda m: (m.score, m.skill.priority, m.skill.name), reverse=True)

        selected: list[SkillMatch] = []
        used = 0
        for match in matches[: max_skills * 3]:
            chunk = len(match.skill.body)
            if not match.skill.body:
                continue
            if used + chunk > budget_chars:
                continue
            selected.append(match)
            used += chunk
            if len(selected) >= max_skills:
                break
        return selected
