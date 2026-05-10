"""Skill models for local markdown-driven skill injection."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """Represents a single skill loaded from markdown frontmatter."""

    name: str
    description: str = ""
    triggers: list[str] = Field(default_factory=list)
    inject: str = Field(default="user_once")
    priority: int = 0
    body: str
    source: str


class SkillMatch(BaseModel):
    """Resolved skill matched for a user prompt."""

    skill: SkillDefinition
    score: int
